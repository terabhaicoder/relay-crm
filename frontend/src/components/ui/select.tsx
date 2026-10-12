"use client";

import {
  Children, Fragment, isValidElement, useEffect, useId, useLayoutEffect,
  useRef, useState, useMemo, type ReactNode, type SelectHTMLAttributes,
  type KeyboardEvent,
} from "react";
import { createPortal } from "react-dom";
import styles from "./select.module.css";

type Option = { value: string; label: string; disabled: boolean; hidden: boolean };
type OptionProps = { children?: ReactNode; value?: string | number; disabled?: boolean; hidden?: boolean };
export type SelectProps = Omit<SelectHTMLAttributes<HTMLSelectElement>, "multiple" | "size" | "onKeyDown" | "onFocus" | "onBlur"> & {
  onValueChange?: (value: string) => void;
  placeholder?: string;
};

function textContent(node: ReactNode): string {
  return Children.toArray(node).map(child => isValidElement<OptionProps>(child)
    ? textContent(child.props.children) : String(child)).join("");
}
function readOptions(children: ReactNode, disabled = false): Option[] {
  return Children.toArray(children).flatMap(child => {
    if (!isValidElement<OptionProps>(child)) return [];
    if (child.type === Fragment || child.type === "optgroup") {
      return readOptions(child.props.children, disabled || !!child.props.disabled);
    }
    if (child.type !== "option") return [];
    const label = textContent(child.props.children);
    return [{ value: String(child.props.value ?? label), label,
      disabled: disabled || !!child.props.disabled, hidden: !!child.props.hidden }];
  });
}

/** A single-select control with real form values and a keyboard-operated listbox. */
export function Select({ children, value, defaultValue, onChange, onValueChange,
  placeholder = "Select an option", disabled, required, name, id, className, style,
  onInvalid, ...props }: SelectProps) {
  const generatedId = useId();
  const listId = `${generatedId}-listbox`;
  const options = useMemo(() => readOptions(children), [children]);
  const initialValue = String(defaultValue ?? options[0]?.value ?? "");
  const [internalValue, setInternalValue] = useState(initialValue);
  const selectedValue = value === undefined ? internalValue : String(value);
  const selected = options.find(option => option.value === selectedValue);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [invalid, setInvalid] = useState(false);
  const [host, setHost] = useState<HTMLElement | null>(null);
  const [placement, setPlacement] = useState({ left: 0, top: 0, width: 0, maxHeight: 300 });
  const rootRef = useRef<HTMLSpanElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const nativeRef = useRef<HTMLSelectElement>(null);
  const popupRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef({ text: "", time: 0 });
  const enabled = options.map((option, index) => !option.disabled && !option.hidden ? index : -1).filter(index => index >= 0);

  // A wrapping label keeps working when callers replace their native select.
  useLayoutEffect(() => {
    const trigger = triggerRef.current;
    if (!trigger || props["aria-label"] || props["aria-labelledby"]) return;
    const label = trigger.labels?.[0] ?? trigger.closest("label");
    if (!label) return;
    const clone = label.cloneNode(true) as HTMLElement;
    clone.querySelectorAll("[data-relay-select-root]").forEach(element => element.remove());
    const text = clone.textContent?.replace(/\s+/g, " ").trim();
    if (text) trigger.setAttribute("aria-label", text);
  });

  useEffect(() => {
    const form = nativeRef.current?.form;
    if (!form) return;
    const reset = () => {
      if (value === undefined) setInternalValue(initialValue);
      setInvalid(false);
      setOpen(false);
      queueMicrotask(() => {
        if (nativeRef.current) nativeRef.current.value = value === undefined ? initialValue : String(value);
      });
    };
    form.addEventListener("reset", reset);
    return () => form.removeEventListener("reset", reset);
  }, [initialValue, value]);

  useLayoutEffect(() => {
    if (!open) return;
    const position = () => {
      const trigger = triggerRef.current;
      if (!trigger) return;
      const rect = trigger.getBoundingClientRect();
      const viewport = window.visualViewport;
      const width = viewport?.width ?? window.innerWidth;
      const height = viewport?.height ?? window.innerHeight;
      const x = viewport?.offsetLeft ?? 0;
      const y = viewport?.offsetTop ?? 0;
      const popupWidth = Math.min(Math.max(rect.width, 160), width - 16);
      const below = y + height - rect.bottom - 14;
      const above = rect.top - y - 14;
      const preferredHeight = Math.min(312, options.filter(option => !option.hidden).length * 40 + 12);
      const upward = below < preferredHeight && above > below;
      const maxHeight = Math.max(40, Math.min(preferredHeight, upward ? above : below));
      setPlacement({ left: Math.max(x + 8, Math.min(rect.left, x + width - popupWidth - 8)),
        top: upward ? rect.top - maxHeight - 6 : rect.bottom + 6,
        width: popupWidth, maxHeight });
    };
    const outside = (event: PointerEvent) => {
      if (event.target instanceof Node && !rootRef.current?.contains(event.target) && !popupRef.current?.contains(event.target)) setOpen(false);
    };
    const escape = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        setOpen(false);
        triggerRef.current?.focus();
      }
    };
    position();
    window.addEventListener("resize", position);
    window.addEventListener("scroll", position, true);
    window.visualViewport?.addEventListener("resize", position);
    window.visualViewport?.addEventListener("scroll", position);
    document.addEventListener("pointerdown", outside, true);
    document.addEventListener("keydown", escape, true);
    const observer = new ResizeObserver(position);
    if (triggerRef.current) observer.observe(triggerRef.current);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", position);
      window.removeEventListener("scroll", position, true);
      window.visualViewport?.removeEventListener("resize", position);
      window.visualViewport?.removeEventListener("scroll", position);
      document.removeEventListener("pointerdown", outside, true);
      document.removeEventListener("keydown", escape, true);
    };
  }, [open, options]); // Reposition if the option collection changes.

  useLayoutEffect(() => {
    if (!open) return;
    const popup = popupRef.current;
    const option = popup?.querySelector<HTMLElement>(`[data-option-index="${active}"]`);
    if (!popup || !option) return;
    if (option.offsetTop < popup.scrollTop) popup.scrollTop = option.offsetTop;
    else if (option.offsetTop + option.offsetHeight > popup.scrollTop + popup.clientHeight) popup.scrollTop = option.offsetTop + option.offsetHeight - popup.clientHeight;
  }, [active, open]);

  function show(index?: number) {
    if (disabled || triggerRef.current?.matches(":disabled")) return;
    setHost(triggerRef.current?.closest<HTMLElement>('[role="dialog"]') ?? document.body);
    setActive(index ?? enabled.find(index => options[index]?.value === selectedValue) ?? enabled[0] ?? -1);
    setOpen(true);
    searchRef.current = { text: "", time: 0 };
  }
  function choose(index: number) {
    const option = options[index];
    if (!option || option.disabled || disabled || triggerRef.current?.matches(":disabled")) return;
    const native = nativeRef.current;
    if (native && option.value !== selectedValue) {
      native.value = option.value;
      native.dispatchEvent(new Event("change", { bubbles: true }));
    }
    setOpen(false);
    triggerRef.current?.focus();
  }
  function keydown(event: KeyboardEvent<HTMLButtonElement>) {
    const key = event.key;
    if (key === "Tab") { setOpen(false); return; }
    if (["ArrowDown", "ArrowUp", "Home", "End"].includes(key)) {
      event.preventDefault();
      const index = key === "Home" ? enabled[0] : key === "End" ? enabled.at(-1)
        : enabled[(enabled.indexOf(active) + (key === "ArrowDown" ? 1 : -1) + enabled.length) % enabled.length];
      if (!open) show(key === "Home" || key === "End" ? index : undefined);
      else setActive(index ?? -1);
      return;
    }
    if (key === "Enter" || key === " ") {
      event.preventDefault();
      if (open) choose(active); else show();
      return;
    }
    if (key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
      event.preventDefault();
      const now = Date.now();
      const previous = now - searchRef.current.time < 700 ? searchRef.current.text : "";
      const query = `${previous}${key.toLocaleLowerCase()}`;
      const repeated = query.split("").every(char => char === query[0]);
      const prefix = repeated ? query[0] : query;
      const start = repeated ? enabled.indexOf(active) + 1 : Math.max(0, enabled.indexOf(active));
      const ordered = [...enabled.slice(start), ...enabled.slice(0, start)];
      const match = ordered.find(index => options[index]?.label.toLocaleLowerCase().startsWith(prefix ?? ""));
      if (!open) show(match); else if (match !== undefined) setActive(match);
      searchRef.current = { text: query, time: now };
    }
  }

  return <span ref={rootRef} className={styles.root} data-relay-select-root="">
    <button ref={triggerRef} type="button" id={id ?? `${generatedId}-trigger`} role="combobox"
      className={`${styles.trigger} ${className ?? ""}`} style={style}
      disabled={disabled} aria-required={required || undefined}
      aria-invalid={props["aria-invalid"] || invalid || undefined}
      aria-label={props["aria-label"]} aria-labelledby={props["aria-labelledby"]}
      aria-describedby={props["aria-describedby"]} title={props.title}
      aria-expanded={open && !disabled} aria-controls={open ? listId : undefined}
      aria-haspopup="listbox" aria-activedescendant={open && active >= 0 ? `${listId}-${active}` : undefined}
      onClick={() => open ? setOpen(false) : show()} onKeyDown={keydown}>
      <span className={styles.value}>{selected?.label || placeholder}</span>
      <svg className={styles.chevron} viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="m4 6 4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
    </button>
    <select {...props} ref={nativeRef} className={styles.native} tabIndex={-1} aria-hidden="true"
      name={name} form={props.form} value={selectedValue} disabled={disabled} required={required}
      onInvalid={event => { event.preventDefault(); setInvalid(true); triggerRef.current?.focus(); onInvalid?.(event); }}
      onChange={event => {
        if (value === undefined) setInternalValue(event.target.value);
        setInvalid(false);
        onChange?.(event);
        onValueChange?.(event.target.value);
      }}>{children}</select>
    {open && !disabled && host && createPortal(<div ref={popupRef} id={listId} role="listbox"
      aria-labelledby={props["aria-labelledby"] ?? id ?? `${generatedId}-trigger`}
      className={styles.popup} style={placement} data-relay-select-listbox="">
      {options.map((option, index) => !option.hidden && <div key={`${option.value}-${index}`}
        id={`${listId}-${index}`} role="option" aria-selected={option.value === selectedValue}
        aria-disabled={option.disabled || undefined} data-active={index === active || undefined}
        data-option-index={index} className={styles.option}
        onMouseDown={event => event.preventDefault()}
        onPointerMove={() => { if (!option.disabled) setActive(index); }}
        onClick={() => choose(index)}>
        <span>{option.label || placeholder}</span>
        {option.value === selectedValue && <svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="m3 8 3 3 7-7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" /></svg>}
      </div>)}
      {!options.some(option => !option.hidden) && <div className={styles.empty}>No options available</div>}
    </div>, host)}
  </span>;
}
