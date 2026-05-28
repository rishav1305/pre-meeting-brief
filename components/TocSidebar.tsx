export type TocItem = {
  id: string;
  label: string;
};

export function TocSidebar({ items }: { items: TocItem[] }) {
  if (items.length === 0) return null;
  return (
    <nav
      aria-label="Table of contents"
      className="sticky top-8 hidden h-fit w-56 shrink-0 self-start text-xs text-slate-600 lg:block"
    >
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
        On this page
      </p>
      <ul className="space-y-1.5">
        {items.map((item) => (
          <li key={item.id}>
            <a
              href={`#${item.id}`}
              className="block leading-snug text-slate-600 transition-colors hover:text-slate-900"
            >
              {item.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
