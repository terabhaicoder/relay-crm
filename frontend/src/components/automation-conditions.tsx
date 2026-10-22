"use client";

import { Select } from "@/components/ui/select";

import type { Condition } from "@/lib/api/schema";

const fieldNames: [Condition["field"], string][] = [
  ["status", "Status"],
  ["source", "Lead source"],
  ["priority", "Priority"],
  ["score", "Lead score"],
  ["amount", "Deal value"],
  ["value", "Lead value"],
  ["company", "Company"],
];

export const automationTriggers = ["leads.created", "leads.updated", "leads.converted", "deals.created", "deals.won", "deals.lost", "deals.stage_changed", "tickets.created", "tickets.updated", "activities.created", "activities.completed"];
export function conditionFields(trigger: string): Condition["field"][] {
  if (trigger.startsWith("leads.")) return ["status", "source", "score", "value", "company"];
  if (trigger.startsWith("deals.")) return ["status", "amount"];
  return ["status", "priority"];
}

export function AutomationConditions({
  value,
  onChange,
  trigger,
}: {
  value: Condition[];
  onChange: (value: Condition[]) => void;
  trigger: string;
}) {
  const update = (index: number, patch: Partial<Condition>) =>
    onChange(
      value.map((condition, position) =>
        position === index ? { ...condition, ...patch } : condition,
      ),
    );

  return (
    <section className="context-action">
      <h3>Only when these conditions match</h3>
      <p>
        All conditions must match. Leave this empty to run on every matching
        event.
      </p>
      <p>Conditions use fields available on this event. Changing the trigger removes conditions that no longer apply.</p>
      {value.map((condition, index) => (
        <div className="form-grid" key={index} style={{ marginTop: 16 }}>
          <label>
            Field
            <Select
              aria-label={`Condition ${index + 1} field`}
              value={condition.field}
              onChange={(event) => {
                const field = event.target.value as Condition["field"];
                update(index, {
                  field,
                  ...(condition.operator === "gte" &&
                  !["score", "amount", "value"].includes(field)
                    ? { operator: "equals" }
                    : {}),
                });
              }}
            >
              {fieldNames.filter(([field]) => conditionFields(trigger).includes(field)).map(([field, label]) => (
                <option value={field} key={field}>
                  {label}
                </option>
              ))}
            </Select>
          </label>
          <label>
            Comparison
            <Select
              aria-label={`Condition ${index + 1} comparison`}
              value={condition.operator ?? "equals"}
              onChange={(event) =>
                update(index, {
                  operator: event.target.value as Condition["operator"],
                })
              }
            >
              <option value="equals">Equals</option>
              <option value="contains">Contains</option>
              {["score", "amount", "value"].includes(condition.field) && (
                <option value="gte">At least</option>
              )}
            </Select>
          </label>
          <label>
            Value
            <input
              aria-label={`Condition ${index + 1} value`}
              value={condition.value}
              maxLength={300}
              required
              onChange={(event) => update(index, { value: event.target.value })}
            />
          </label>
          <div className="row-actions">
            <button
              type="button"
              className="button subtle"
              aria-label={`Remove condition ${index + 1}`}
              onClick={() =>
                onChange(value.filter((_, position) => position !== index))
              }
            >
              Remove condition
            </button>
          </div>
        </div>
      ))}
      <button
        type="button"
        className="button secondary"
        style={{ marginTop: 16 }}
        disabled={value.length >= 10}
        onClick={() =>
          onChange([
            ...value,
            { field: conditionFields(trigger)[0]!, operator: "equals", value: "" },
          ])
        }
      >
        Add condition
      </button>
    </section>
  );
}
