export default function EmptyPanel({
  title,
  text,
}: {
  title: string;
  text: string;
}) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900 p-6">
      <h3 className="font-semibold text-slate-100">{title}</h3>
      <p className="mt-2 text-sm text-slate-400">{text}</p>
    </section>
  );
}
