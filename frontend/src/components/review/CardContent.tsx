/** Renders card-face markdown with inline/display math via KaTeX. */

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

export interface CardContentProps {
  markdown: string;
}

export const CardContent: React.FC<CardContentProps> = ({ markdown }) => {
  return (
    <div className="max-w-none text-app">
      <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
        {markdown}
      </ReactMarkdown>
    </div>
  );
};

CardContent.displayName = 'CardContent';
