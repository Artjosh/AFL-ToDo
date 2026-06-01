/**
 * Avatar circular com as iniciais do email e cor derivada (estilo Trello/Jira).
 */
"use client";

const COLORS = [
  "#6C5CE7", "#0984e3", "#00b894", "#e17055", "#e84393",
  "#fdcb6e", "#00cec9", "#a29bfe", "#fab1a0", "#55efc4",
];

function colorFor(seed: string): string {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = seed.charCodeAt(i) + ((hash << 5) - hash);
  }
  return COLORS[Math.abs(hash) % COLORS.length];
}

function initials(email: string): string {
  const name = email.split("@")[0];
  const parts = name.split(/[.\-_]/).filter(Boolean);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
}

export default function Avatar({
  email,
  size = 24,
  title,
}: {
  email: string;
  size?: number;
  title?: string;
}) {
  return (
    <span
      title={title ?? email}
      className="inline-flex shrink-0 items-center justify-center rounded-full font-bold text-white ring-2 ring-surface"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.4,
        background: colorFor(email),
      }}
    >
      {initials(email)}
    </span>
  );
}
