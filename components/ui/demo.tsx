import GlassmorphismCta from "@/components/ui/glassmorphism-cta";

export default function Default() {
  return (
    <div className="grid min-h-screen w-full place-items-center bg-[#0a0b14] p-4">
      <div className="flex flex-col items-center gap-6">
        <div className="text-center text-white">
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">TravelShield AI</h1>
          <p className="mt-2 text-sm text-slate-400">Intelligent Multimodal Travel Disruption Recovery Engine</p>
        </div>
        <GlassmorphismCta 
          label="Recover My Journey" 
          avatarSrc="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80"
          avatarAlt="AI Travel Advisor"
        />
      </div>
    </div>
  );
}
