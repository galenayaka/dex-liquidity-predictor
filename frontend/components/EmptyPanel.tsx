export default function EmptyPanel({
  title,
  text,
}: {
  title: string;
  text: string;
}) {
  return (
    <section className="panel p-4">
      <h3 className="text-xs font-bold uppercase tracking-[0.18em] text-noir-amber">
        {title}
      </h3>
      <p className="mt-2 text-xs uppercase tracking-[0.06em] text-noir-dim">
        {text}
      </p>
    </section>
  );
}
