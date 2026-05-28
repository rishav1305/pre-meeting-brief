import { promises as fs } from "fs";
import path from "path";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSlug from "rehype-slug";
import rehypeAutolinkHeadings from "rehype-autolink-headings";

export const dynamic = "force-static";

export default async function ApproachPage() {
  const filePath = path.join(process.cwd(), "docs", "approach.md");
  const source = await fs.readFile(filePath, "utf8");

  return (
    <main className="prose prose-slate prose-headings:tracking-tight prose-table:text-sm mx-auto max-w-3xl px-6 py-12">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSlug, rehypeAutolinkHeadings]}
      >
        {source}
      </ReactMarkdown>
    </main>
  );
}
