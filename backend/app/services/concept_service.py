"""Concept (OKF markdown file) CRUD over a git-backed workspace bundle.

Every mutation writes the file (and commits) via :class:`BundleRepo`, then keeps
the FalkorDB projection in sync via :class:`IndexService`, then records an audit
entry. The files are the source of truth; the graph is derived. Version history
comes from git — there is no bespoke version model.
"""

from __future__ import annotations

from app.api.deps import CurrentUser
from app.api.errors import ConflictError, NotFoundError
from app.events.types import EventType
from app.okf.concept import Concept, parse_concept, to_markdown
from app.schemas.concept import (
    ConceptOut,
    ConceptRef,
    ConceptSummary,
    VersionEntry,
)
from app.services.audit_service import AuditService
from app.services.eval_history import record_eval_run
from app.services.index_service import IndexService, is_reserved
from app.storage import paths
from app.storage.repo import BundleRepo

# Frontmatter keys we surface as first-class fields (everything else is extra).
_KNOWN = ("type", "title", "description", "runtime", "tags", "capabilities", "sources")


def _concept_path(folder_path: str, name: str) -> str:
    slug = paths.slugify(name)
    leaf = f"{slug}.md"
    folder = folder_path.strip("/")
    return f"{folder}/{leaf}" if folder else leaf


class ConceptService:
    def __init__(self, db, user: CurrentUser):
        self.db = db
        self.user = user
        self.index = IndexService()
        self.audit = AuditService(db)

    def _bundle(self, workspace_id: str) -> BundleRepo:
        return BundleRepo(workspace_id)

    # ── reads ──
    def _to_out(self, workspace_id: str, c: Concept, hist: list[dict]) -> ConceptOut:
        bundle_files = {p for p in self._bundle(workspace_id).list_files(".md")}
        refs = [
            ConceptRef(path=link, title=None, type=None)
            for link in c.links
            if link in bundle_files
        ]
        extra = {k: v for k, v in c.frontmatter.items() if k not in _KNOWN}
        return ConceptOut(
            workspace_id=workspace_id,
            path=c.path,
            type=c.type,
            title=c.title,
            description=c.description,
            runtime=c.runtime,
            tags=c.tags,
            capabilities=c.capabilities,
            sources=c.sources,
            body=c.body,
            frontmatter=extra,
            links=c.links,
            references=refs,
            created_at=hist[-1]["ts"] if hist else None,
            updated_at=hist[0]["ts"] if hist else None,
        )

    def get(self, workspace_id: str, path: str) -> ConceptOut:
        bundle = self._bundle(workspace_id)
        if not bundle.exists or not bundle.exists_file(path):
            raise NotFoundError("Concept not found")
        c = parse_concept(path, bundle.read_file(path))
        return self._to_out(workspace_id, c, bundle.history(path))

    def list_concepts(self, workspace_id: str) -> list[ConceptSummary]:
        bundle = self._bundle(workspace_id)
        if not bundle.exists:
            return []
        out: list[ConceptSummary] = []
        for path in bundle.list_files(".md"):
            if is_reserved(path):
                continue
            c = parse_concept(path, bundle.read_file(path))
            out.append(
                ConceptSummary(
                    workspace_id=workspace_id,
                    path=c.path,
                    type=c.type,
                    title=c.title,
                    description=c.description,
                    runtime=c.runtime,
                    tags=c.tags,
                    capabilities=c.capabilities,
                    sources=c.sources,
                )
            )
        return out

    async def evaluate(self, workspace_id: str, path: str) -> dict:
        """Run the six-evaluator supervisor over a concept; returns a report dict."""
        from app.evals.supervisor import EvalSupervisor

        bundle = self._bundle(workspace_id)
        if not bundle.exists or not bundle.exists_file(path):
            raise NotFoundError("Concept not found")
        concept = parse_concept(path, bundle.read_file(path))
        bundle_files = [p for p in bundle.list_files(".md")]
        report = await EvalSupervisor().evaluate(concept, bundle_files)
        out = report.to_dict()
        await record_eval_run(
            workspace_id=workspace_id,
            concept_path=path,
            kind="fast",
            score=out.get("overall_score"),
            passed=out.get("passed"),
            payload=out,
            actor_id=self.user.id,
        )
        return out

    async def deep_evaluate(self, workspace_id: str, path: str, n_cases: int = 5) -> dict:
        """Agentic LLM-as-judge evaluation (generate cases, with/without, score)."""
        from app.evals.deep import DeepEvaluator

        bundle = self._bundle(workspace_id)
        if not bundle.exists or not bundle.exists_file(path):
            raise NotFoundError("Concept not found")
        concept = parse_concept(path, bundle.read_file(path))
        report = await DeepEvaluator().evaluate(concept, n_cases=n_cases)
        out = report.to_dict()
        if out.get("available"):
            await record_eval_run(
                workspace_id=workspace_id,
                concept_path=path,
                kind="deep",
                score=out.get("effectiveness_avg"),
                summary=out.get("summary"),
                payload=out,
                actor_id=self.user.id,
            )
        return out

    # ── interactive evaluation (grade vs expected) ──
    def _concept_or_404(self, workspace_id: str, path: str) -> Concept:
        bundle = self._bundle(workspace_id)
        if not bundle.exists or not bundle.exists_file(path):
            raise NotFoundError("Concept not found")
        return parse_concept(path, bundle.read_file(path))

    def get_eval_cases(self, workspace_id: str, path: str) -> list[dict]:
        """Load the versioned eval suite for a concept (empty list if none)."""
        from app.okf import eval_cases

        bundle = self._bundle(workspace_id)
        if not bundle.exists or not bundle.exists_file(path):
            raise NotFoundError("Concept not found")
        cpath = eval_cases.cases_path(path)
        if not bundle.exists_file(cpath):
            return []
        return eval_cases.parse_cases(bundle.read_file(cpath))

    def save_eval_cases(self, workspace_id: str, path: str, cases: list[dict]) -> list[dict]:
        """Persist the eval suite as a git-versioned sibling file."""
        from app.okf import eval_cases

        bundle = self._bundle(workspace_id)
        if not bundle.exists or not bundle.exists_file(path):
            raise NotFoundError("Concept not found")
        cpath = eval_cases.cases_path(path)
        bundle.write_file(
            cpath, eval_cases.dump_cases(cases), f"update eval cases {cpath}", self.user.id
        )
        return eval_cases.parse_cases(bundle.read_file(cpath))

    async def suggest_eval_cases(self, workspace_id: str, path: str, n: int = 5) -> list[dict]:
        """LLM-drafted {input, expected} cases; expected is blank when it can't infer."""
        from app.evals.agent import EvalAgent

        concept = self._concept_or_404(workspace_id, path)
        drafts = await EvalAgent().suggest_cases(concept, n)
        return [{"input": d.input, "expected": d.expected} for d in drafts]

    async def grade_eval(self, workspace_id: str, path: str, cases: list[dict]) -> dict:
        """Run the skill on each case and grade actual output vs expected."""
        from app.evals.grade import GradeEvaluator

        concept = self._concept_or_404(workspace_id, path)
        report = await GradeEvaluator().evaluate(concept, cases)
        out = report.to_dict()
        if out.get("available") and out.get("cases"):
            await record_eval_run(
                workspace_id=workspace_id,
                concept_path=path,
                kind="grade",
                score=round(float(out.get("pass_rate", 0.0)) * 100, 1),
                summary=out.get("summary"),
                payload={k: v for k, v in out.items() if k != "cases"},
                actor_id=self.user.id,
            )
        return out

    def graph(self, workspace_id: str) -> dict:
        """The workspace concept graph (nodes + reference edges) for visualization."""
        return self.index.repo.graph(workspace_id)

    async def reindex(self, workspace_id: str) -> dict:
        """Rebuild the graph projection from files and heal any degraded embeddings."""
        result = await self.index.reindex_workspace(workspace_id)
        healed = await self.index.embed_pending(workspace_id)
        return {
            "documents": result.documents,
            "references": result.references,
            "embedded": result.embedded + healed,
            "pending": len(self.index.repo.pending_embedding_paths(workspace_id)),
            "orphans": result.orphans,
        }

    def neighborhood(self, workspace_id: str, path: str) -> dict | None:
        return self.index.repo.neighborhood(workspace_id=workspace_id, path=path)

    async def search(self, workspace_id: str, q: str, k: int = 10) -> list[dict]:
        """Semantic search over the workspace's concept projection."""
        vec, is_real = await self.index.provider.embed_one_checked(q)
        if not is_real:
            # The query embedding degraded (rate-limited); a hash vector can't be
            # compared against the real stored vectors, so return nothing rather
            # than misleading matches. The caller can retry.
            return []
        hits = self.index.repo.search(workspace_id=workspace_id, embedding=vec, k=k)
        results = []
        for props, score in hits:
            results.append(
                {
                    "path": props.get("path"),
                    "title": props.get("title"),
                    "type": props.get("type"),
                    "runtime": props.get("runtime"),
                    "description": props.get("description"),
                    "score": score,
                }
            )
        return results

    def history(self, workspace_id: str, path: str) -> list[VersionEntry]:
        bundle = self._bundle(workspace_id)
        if not bundle.exists or not bundle.exists_file(path):
            raise NotFoundError("Concept not found")
        return [VersionEntry(**e) for e in bundle.history(path)]

    # ── writes ──
    async def create(
        self,
        *,
        workspace_id: str,
        folder_path: str,
        name: str,
        type: str,
        description: str | None,
        runtime: str | None,
        tags: list[str],
        capabilities: list[str],
        sources: list[str] | None = None,
        body: str,
        frontmatter: dict,
    ) -> ConceptOut:
        bundle = BundleRepo.init(workspace_id)
        path = _concept_path(folder_path, name)
        if bundle.exists_file(path):
            raise ConflictError("A concept with that name already exists in this folder")
        fields = {
            "type": type,
            "title": name,
            "description": description,
            "runtime": runtime,
            "tags": tags or None,
            "capabilities": capabilities or None,
            "sources": sources or None,
            **frontmatter,
        }
        bundle.write_file(path, to_markdown(fields, body), f"create {path}", self.user.id)
        await self.index.index_concept(workspace_id, path)
        await self.audit.record(
            actor_id=self.user.id,
            action=EventType.CONCEPT_CREATED,
            resource_type="Concept",
            resource_id=path,
            workspace_id=workspace_id,
            payload={"type": type, "path": path},
        )
        return self.get(workspace_id, path)

    async def update(
        self,
        *,
        workspace_id: str,
        path: str,
        title: str | None = None,
        type: str | None = None,
        description: str | None = None,
        runtime: str | None = None,
        tags: list[str] | None = None,
        capabilities: list[str] | None = None,
        sources: list[str] | None = None,
        body: str | None = None,
        frontmatter: dict | None = None,
    ) -> ConceptOut:
        bundle = self._bundle(workspace_id)
        if not bundle.exists or not bundle.exists_file(path):
            raise NotFoundError("Concept not found")
        current = parse_concept(path, bundle.read_file(path))

        merged = dict(current.frontmatter)
        if frontmatter is not None:
            merged.update(frontmatter)
        if title is not None:
            merged["title"] = title
        if type is not None:
            merged["type"] = type
        if description is not None:
            merged["description"] = description
        if runtime is not None:
            merged["runtime"] = runtime
        if tags is not None:
            merged["tags"] = tags
        if capabilities is not None:
            merged["capabilities"] = capabilities
        if sources is not None:
            merged["sources"] = sources
        new_body = current.body if body is None else body

        bundle.write_file(path, to_markdown(merged, new_body), f"update {path}", self.user.id)
        await self.index.index_concept(workspace_id, path)
        await self.audit.record(
            actor_id=self.user.id,
            action=EventType.CONCEPT_UPDATED,
            resource_type="Concept",
            resource_id=path,
            workspace_id=workspace_id,
        )
        return self.get(workspace_id, path)

    async def move(self, *, workspace_id: str, src_path: str, dst_folder_path: str) -> ConceptOut:
        bundle = self._bundle(workspace_id)
        if not bundle.exists or not bundle.exists_file(src_path):
            raise NotFoundError("Concept not found")
        leaf = src_path.rsplit("/", 1)[-1]
        folder = dst_folder_path.strip("/")
        dst = f"{folder}/{leaf}" if folder else leaf
        if dst == src_path:
            return self.get(workspace_id, src_path)
        if bundle.exists_file(dst):
            raise ConflictError("A concept with that name already exists at the destination")
        bundle.move_path(src_path, dst, f"move {src_path} -> {dst}", self.user.id)
        self.index.remove_concept(workspace_id, src_path)
        await self.index.index_concept(workspace_id, dst)
        await self.audit.record(
            actor_id=self.user.id,
            action=EventType.CONCEPT_MOVED,
            resource_type="Concept",
            resource_id=dst,
            workspace_id=workspace_id,
            payload={"from": src_path, "to": dst},
        )
        return self.get(workspace_id, dst)

    async def delete(self, *, workspace_id: str, path: str) -> None:
        bundle = self._bundle(workspace_id)
        if not bundle.exists or not bundle.exists_file(path):
            raise NotFoundError("Concept not found")
        bundle.delete_path(path, f"delete {path}", self.user.id)
        self.index.remove_concept(workspace_id, path)
        await self.audit.record(
            actor_id=self.user.id,
            action=EventType.CONCEPT_DELETED,
            resource_type="Concept",
            resource_id=path,
            workspace_id=workspace_id,
        )

    async def publish(self, *, workspace_id: str, path: str, version: str) -> ConceptOut:
        bundle = self._bundle(workspace_id)
        if not bundle.exists or not bundle.exists_file(path):
            raise NotFoundError("Concept not found")
        # Tag name encodes the file so multiple concepts can be versioned in one repo.
        tag = f"{paths.slugify(path.removesuffix('.md'))}-v{version}"
        bundle.tag(tag, f"publish {path} v{version}")
        # Project the published version into the graph (Concept)-[:HAS_VERSION]->(Version).
        self.index.rebuild_versions(workspace_id, bundle)
        # List it in the marketplace catalog (idempotent per concept+version).
        from app.services.marketplace_service import MarketplaceService

        await MarketplaceService(self.db, self.user).upsert_on_publish(
            workspace_id=workspace_id, path=path, version=version
        )
        await self.audit.record(
            actor_id=self.user.id,
            action=EventType.CONCEPT_PUBLISHED,
            resource_type="Concept",
            resource_id=path,
            workspace_id=workspace_id,
            payload={"version": version, "tag": tag},
        )
        return self.get(workspace_id, path)

    # ── version management (history / preview / diff / restore) ──
    def versions(self, workspace_id: str, path: str) -> list[dict]:
        """Published-version lineage for a concept (from the graph projection)."""
        self._concept_or_404(workspace_id, path)
        return self.index.repo.versions_for(workspace_id=workspace_id, path=path)

    def version_content(self, workspace_id: str, path: str, ref: str) -> dict:
        """Read-only snapshot of a concept as of a git ref (commit sha or tag)."""
        bundle = self._bundle(workspace_id)
        if not bundle.exists or not bundle.exists_file(path):
            raise NotFoundError("Concept not found")
        raw = bundle.read_file_at(path, ref)
        c = parse_concept(path, raw)
        return {"path": path, "ref": ref, "title": c.title, "body": c.body, "content": raw}

    def diff_versions(self, workspace_id: str, path: str, a: str, b: str) -> dict:
        """Unified diff of a concept between two refs."""
        bundle = self._bundle(workspace_id)
        if not bundle.exists or not bundle.exists_file(path):
            raise NotFoundError("Concept not found")
        return {"path": path, "a": a, "b": b, "diff": bundle.diff(path, a, b)}

    async def restore_version(self, workspace_id: str, path: str, ref: str) -> ConceptOut:
        """Restore a past version's content as a new commit, then re-index."""
        bundle = self._bundle(workspace_id)
        if not bundle.exists or not bundle.exists_file(path):
            raise NotFoundError("Concept not found")
        bundle.restore(path, ref, f"restore {path} from {ref}", self.user.id)
        await self.index.index_concept(workspace_id, path)
        await self.audit.record(
            actor_id=self.user.id,
            action=EventType.CONCEPT_UPDATED,
            resource_type="Concept",
            resource_id=path,
            workspace_id=workspace_id,
            payload={"restored_from": ref},
        )
        return self.get(workspace_id, path)
