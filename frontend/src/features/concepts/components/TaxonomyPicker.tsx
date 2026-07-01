import { Select } from "antd";
import { useTaxonomyTerms } from "../api/taxonomyApi";

interface Props {
  kind: "capability" | "source";
  value?: string[];
  onChange?: (v: string[]) => void;
  placeholder?: string;
  disabled?: boolean;
}

/**
 * Tag-select seeded from the taxonomy API.
 * Free entry is allowed — a value not in the list is accepted (curated-open).
 */
export function TaxonomyPicker({ kind, value, onChange, placeholder, disabled }: Props) {
  const apiKind = kind === "capability" ? "capabilities" : "sources";
  const { data, isLoading } = useTaxonomyTerms(apiKind);

  const options = (data?.terms ?? []).map((t) => ({
    value: t.key,
    label: t.label,
    title: t.label,
  }));

  return (
    <Select
      mode="tags"
      value={value}
      onChange={onChange}
      options={options}
      loading={isLoading}
      disabled={disabled}
      tokenSeparators={[","]}
      placeholder={placeholder ?? (kind === "capability" ? "e.g. extraction:invoice" : "e.g. pdf, rest-api")}
      allowClear
      style={{ width: "100%" }}
      filterOption={(input, option) =>
        (option?.label ?? "").toLowerCase().includes(input.toLowerCase()) ||
        (option?.value ?? "").toLowerCase().includes(input.toLowerCase())
      }
    />
  );
}
