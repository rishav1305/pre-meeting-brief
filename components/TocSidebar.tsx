"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

export type TocItem = {
  id: string;
  label: string;
  children?: TocItem[];
};

type Props = {
  items: TocItem[];
};

function buildAllIds(items: TocItem[]): string[] {
  return items.flatMap((h2) => [h2.id, ...(h2.children?.map((c) => c.id) ?? [])]);
}

function buildParentMap(items: TocItem[]): Record<string, string> {
  const map: Record<string, string> = {};
  for (const h2 of items) {
    for (const h3 of h2.children ?? []) {
      map[h3.id] = h2.id;
    }
  }
  return map;
}

function useScrollSpy(items: TocItem[]) {
  const [activeId, setActiveId] = useState<string | null>(null);

  useEffect(() => {
    const allIds = buildAllIds(items);
    const elements = allIds
      .map((id) => document.getElementById(id))
      .filter((el): el is HTMLElement => el !== null);
    if (elements.length === 0) return;

    // Track which ids are currently intersecting; pick the topmost.
    const visible = new Map<string, IntersectionObserverEntry>();
    const observer = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            visible.set(e.target.id, e);
          } else {
            visible.delete(e.target.id);
          }
        }
        if (visible.size > 0) {
          const sorted = Array.from(visible.values()).sort(
            (a, b) => a.boundingClientRect.top - b.boundingClientRect.top,
          );
          setActiveId(sorted[0].target.id);
        }
      },
      // Activate when heading enters the top 30% of the viewport.
      { rootMargin: "-80px 0px -70% 0px", threshold: 0 },
    );
    elements.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [items]);

  return activeId;
}

function smoothScrollTo(id: string) {
  const el = document.getElementById(id);
  if (!el) return;
  // Account for sticky top bar (~64-80px). scroll-margin-top in globals.css
  // also handles this for keyboard / direct anchor jumps.
  const y = el.getBoundingClientRect().top + window.scrollY - 80;
  window.scrollTo({ top: y, behavior: "smooth" });
  // Update hash without triggering an additional jump.
  if (history.replaceState) {
    history.replaceState(null, "", `#${id}`);
  }
}

function TocLink({
  item,
  level,
  active,
  activeParent,
}: {
  item: TocItem;
  level: 2 | 3;
  active: boolean;
  activeParent?: boolean;
}) {
  const onClick = useCallback(
    (e: React.MouseEvent<HTMLAnchorElement>) => {
      e.preventDefault();
      smoothScrollTo(item.id);
    },
    [item.id],
  );

  const base =
    level === 2
      ? "block py-1 pl-2 text-sm leading-snug transition-colors"
      : "block py-0.5 pl-2 text-xs leading-snug transition-colors";

  const state = active
    ? "border-l-2 border-slate-900 font-medium text-slate-900"
    : activeParent && level === 2
      ? "border-l-2 border-slate-300 text-slate-700 hover:text-slate-900"
      : "border-l-2 border-transparent text-slate-500 hover:text-slate-800";

  return (
    <a href={`#${item.id}`} onClick={onClick} className={`${base} ${state}`}>
      {item.label}
    </a>
  );
}

function TocTree({
  items,
  activeId,
  expanded,
  toggle,
  parentMap,
  variant,
}: {
  items: TocItem[];
  activeId: string | null;
  expanded: Record<string, boolean>;
  toggle: (id: string) => void;
  parentMap: Record<string, string>;
  variant: "sidebar" | "mobile";
}) {
  const activeParent =
    activeId && parentMap[activeId] ? parentMap[activeId] : activeId;

  return (
    <ul className={variant === "sidebar" ? "space-y-0.5" : "space-y-0.5"}>
      {items.map((h2) => {
        const isExpanded = expanded[h2.id] ?? true;
        const hasChildren = (h2.children?.length ?? 0) > 0;
        const isActive = activeId === h2.id;
        const isActiveParent = activeParent === h2.id && !isActive;
        return (
          <li key={h2.id}>
            <div className="flex items-start gap-0.5">
              {hasChildren ? (
                <button
                  type="button"
                  onClick={() => toggle(h2.id)}
                  aria-label={isExpanded ? "Collapse section" : "Expand section"}
                  aria-expanded={isExpanded}
                  className="mt-1 w-4 shrink-0 text-[10px] text-slate-400 transition-colors hover:text-slate-700"
                >
                  {isExpanded ? "▾" : "▸"}
                </button>
              ) : (
                <span className="mt-1 w-4 shrink-0" aria-hidden />
              )}
              <div className="min-w-0 flex-1">
                <TocLink
                  item={h2}
                  level={2}
                  active={isActive}
                  activeParent={isActiveParent}
                />
              </div>
            </div>
            {hasChildren && isExpanded && (
              <ul className="ml-5 mt-0.5 space-y-0.5 border-l border-slate-100 pl-1">
                {h2.children!.map((h3) => (
                  <li key={h3.id}>
                    <TocLink item={h3} level={3} active={activeId === h3.id} />
                  </li>
                ))}
              </ul>
            )}
          </li>
        );
      })}
    </ul>
  );
}

export function TocSidebar({ items }: Props) {
  const parentMap = useMemo(() => buildParentMap(items), [items]);
  const activeId = useScrollSpy(items);

  const [expanded, setExpanded] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(items.map((i) => [i.id, true])),
  );

  const toggle = useCallback((id: string) => {
    setExpanded((prev) => ({ ...prev, [id]: !(prev[id] ?? true) }));
  }, []);

  const allExpanded = items.every((i) => expanded[i.id] ?? true);

  const setAll = useCallback(
    (value: boolean) => {
      setExpanded(Object.fromEntries(items.map((i) => [i.id, value])));
    },
    [items],
  );

  if (items.length === 0) return null;

  const totalH3 = items.reduce((n, i) => n + (i.children?.length ?? 0), 0);

  return (
    <>
      {/* Desktop sticky sidebar */}
      <nav
        aria-label="Table of contents"
        className="sticky top-8 hidden h-[calc(100vh-4rem)] w-64 shrink-0 self-start overflow-y-auto pr-2 text-slate-600 lg:block"
      >
        <div className="mb-3 flex items-baseline justify-between">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
            On this page
          </p>
          <button
            type="button"
            onClick={() => setAll(!allExpanded)}
            className="text-[10px] text-slate-400 transition-colors hover:text-slate-700"
          >
            {allExpanded ? "Collapse all" : "Expand all"}
          </button>
        </div>
        <p className="mb-2 text-[10px] text-slate-400">
          {items.length} sections · {totalH3} sub-sections
        </p>
        <TocTree
          items={items}
          activeId={activeId}
          expanded={expanded}
          toggle={toggle}
          parentMap={parentMap}
          variant="sidebar"
        />
      </nav>

      {/* Mobile / tablet inline accordion */}
      <details className="mb-6 rounded-md border border-slate-200 bg-slate-50/60 px-4 py-3 lg:hidden">
        <summary className="cursor-pointer text-sm font-medium text-slate-700">
          On this page · {items.length} sections
        </summary>
        <div className="mt-3">
          <TocTree
            items={items}
            activeId={activeId}
            expanded={expanded}
            toggle={toggle}
            parentMap={parentMap}
            variant="mobile"
          />
        </div>
      </details>
    </>
  );
}
