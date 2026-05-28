import { promises as fs } from "fs";
import path from "path";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSlug from "rehype-slug";
import rehypeAutolinkHeadings from "rehype-autolink-headings";

import { TocSidebar, type TocItem } from "@/components/TocSidebar";

export const dynamic = "force-static";

// Matches github-slugger's default behavior (which rehypeSlug uses): lowercase,
// strip punctuation (keep word chars / spaces / dashes), trim, spaces -> dashes.
function slugify(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^\w\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-");
}

function extractTocItems(source: string): TocItem[] {
  const items: TocItem[] = [];
  const regex = /^## (.+)$/gm;
  let match: RegExpExecArray | null;
  while ((match = regex.exec(source)) !== null) {
    const label = match[1].trim();
    items.push({ id: slugify(label), label });
  }
  return items;
}

export default async function ApproachPage() {
  const filePath = path.join(process.cwd(), "docs", "approach.md");
  const source = await fs.readFile(filePath, "utf8");
  const tocItems = extractTocItems(source);

  return (
    <main className="mx-auto flex max-w-5xl gap-10 px-6 py-12">
      <TocSidebar items={tocItems} />
      <article className="prose prose-slate prose-headings:tracking-tight prose-table:text-sm max-w-3xl flex-1">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[rehypeSlug, rehypeAutolinkHeadings]}
        >
          {source}
        </ReactMarkdown>
      </article>
    </main>
  );
}
