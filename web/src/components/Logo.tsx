/**
 * DocuAI wordmark.
 *
 * Two-tone serif treatment: "Docu" in the body color, "AI" in the accent.
 * Keeps the product feeling like a real piece of software rather than a demo.
 */
export function Logo({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const fontSize = {
    sm: "text-base",
    md: "text-[19px]",
    lg: "text-3xl",
  }[size];

  return (
    <span
      className={`font-display font-semibold tracking-tight ${fontSize}`}
      style={{ letterSpacing: "-0.025em" }}
    >
      <span className="text-fg">Docu</span>
      <span className="text-accent">AI</span>
    </span>
  );
}
