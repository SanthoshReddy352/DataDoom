// Renders a plugin's `param_schema` JSON-schema fragment into form controls
// (09 §6) — number inputs with min/max, enums as dropdowns, booleans as
// checkboxes, strings as text. This is the "UI auto-integration" surface: a
// plugin that declares a schema gets config controls with no bespoke frontend.
import type { JsonSchemaFragment, JsonSchemaProperty } from "./types";

const inputClass =
  "ring-focus w-full rounded-control border border-border bg-surface-2 px-2.5 py-1.5 font-mono text-sm outline-none focus:border-primary disabled:opacity-70";

function constraints(p: JsonSchemaProperty): string {
  const bits: string[] = [];
  if (p.type) bits.push(p.type);
  if (p.minimum !== undefined) bits.push(`≥ ${p.minimum}`);
  if (p.maximum !== undefined) bits.push(`≤ ${p.maximum}`);
  return bits.join(" · ");
}

function Control({ prop, disabled }: { prop: JsonSchemaProperty; disabled: boolean }) {
  const def = prop.default;
  if (prop.enum && prop.enum.length > 0) {
    return (
      <select className={inputClass} disabled={disabled} defaultValue={def as string}>
        {prop.enum.map((o) => (
          <option key={String(o)} value={String(o)}>
            {String(o)}
          </option>
        ))}
      </select>
    );
  }
  if (prop.type === "boolean") {
    return (
      <input
        type="checkbox"
        disabled={disabled}
        defaultChecked={Boolean(def)}
        className="h-4 w-4 accent-[var(--primary)]"
      />
    );
  }
  if (prop.type === "number" || prop.type === "integer") {
    return (
      <input
        type="number"
        disabled={disabled}
        min={prop.minimum}
        max={prop.maximum}
        step={prop.type === "integer" ? 1 : "any"}
        defaultValue={def as number}
        placeholder={constraints(prop)}
        className={inputClass}
      />
    );
  }
  return (
    <input
      type="text"
      disabled={disabled}
      defaultValue={def as string}
      placeholder={prop.type ?? "string"}
      className={inputClass}
    />
  );
}

export function SchemaFields({
  schema,
  disabled = false,
}: {
  schema: JsonSchemaFragment;
  disabled?: boolean;
}) {
  const props = schema.properties ?? {};
  const names = Object.keys(props);
  const required = new Set(schema.required ?? []);
  if (names.length === 0) {
    return <p className="text-xs text-text-faint">No configurable parameters.</p>;
  }
  return (
    <div className="flex flex-col gap-3">
      {names.map((name) => {
        const prop = props[name];
        return (
          <label key={name} className="block">
            <span className="flex items-baseline justify-between">
              <span className="text-xs font-medium text-text">
                {prop.title ?? name}
                {required.has(name) && <span className="text-primary"> *</span>}
              </span>
              <span className="font-mono text-[10px] text-text-faint">{constraints(prop)}</span>
            </span>
            <span className="mt-1 block">
              <Control prop={prop} disabled={disabled} />
            </span>
            {prop.description && (
              <span className="mt-1 block text-[11px] text-text-muted">{prop.description}</span>
            )}
          </label>
        );
      })}
    </div>
  );
}
