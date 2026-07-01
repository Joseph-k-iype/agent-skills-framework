import { Select } from "antd";
import { useParams } from "react-router-dom";
import { useConcepts } from "../api/conceptApi";

interface Props {
  value?: string | null;
  onChange?: (v: string | null) => void;
  disabled?: boolean;
}

/**
 * Selects an existing concept path as the parent of the current concept.
 * The current concept's own path is excluded from the list.
 */
export function ParentConceptSelect({ value, onChange, disabled }: Props) {
  const params = useParams();
  const workspaceId = params.workspaceId ?? "";
  const currentPath = params["*"] ?? "";

  const { data: concepts, isLoading } = useConcepts(workspaceId);

  const options = (concepts ?? [])
    .filter((c) => c.path !== currentPath)
    .map((c) => ({
      value: c.path,
      label: `${c.title} — ${c.path}`,
    }));

  return (
    <Select
      showSearch
      allowClear
      value={value ?? undefined}
      onChange={(v) => onChange?.(v ?? null)}
      options={options}
      loading={isLoading}
      disabled={disabled}
      optionFilterProp="label"
      placeholder="Select a parent concept path (optional)"
      style={{ width: "100%" }}
    />
  );
}
