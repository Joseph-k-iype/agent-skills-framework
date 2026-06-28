import { Empty } from "antd";
import { PageHeader } from "./PageHeader";

/** Temporary page used for routes whose feature lands in a later phase. */
export function Placeholder({ title, eyebrow, phase }: { title: string; eyebrow?: string; phase?: string }) {
  return (
    <div>
      <PageHeader eyebrow={eyebrow} title={title} />
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={phase ? `Arrives in ${phase}.` : "Coming soon."}
        style={{ marginTop: 80 }}
      />
    </div>
  );
}
