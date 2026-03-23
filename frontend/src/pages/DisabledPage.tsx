interface DisabledPageProps {
  title: string;
  phase: string;
}
export function DisabledPage({ title, phase }: DisabledPageProps) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center">
      <h1 className="text-2xl font-bold mb-2">{title}</h1>
      <p className="text-muted-foreground">Available in Phase {phase}.</p>
    </div>
  );
}
