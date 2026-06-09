export default function Navbar() {
  return (
    <nav className="bg-forest-900 text-white relative overflow-hidden">
      {/* Subtle topographic pattern overlay */}
      <div
        className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage: `repeating-linear-gradient(
            0deg, transparent, transparent 28px, rgba(255,255,255,0.6) 28px, rgba(255,255,255,0.6) 29px
          ), repeating-linear-gradient(
            90deg, transparent, transparent 60px, rgba(255,255,255,0.3) 60px, rgba(255,255,255,0.3) 61px
          )`,
        }}
      />
      <div className="absolute inset-x-0 bottom-0 h-px bg-forest-700" />

      <div className="relative max-w-screen-2xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3.5">
          <div className="w-9 h-9 rounded-xl bg-forest-700/60 border border-forest-600/40 flex items-center justify-center flex-shrink-0">
            <svg className="w-5 h-5 text-forest-300" viewBox="0 0 24 24" fill="currentColor">
              <path d="M17 8C8 10 5.9 16.17 3.82 21.34L5.71 22l1-2.3A4.49 4.49 0 0 0 8 20C19 20 22 3 22 3c-1 2-8 2-8 2 0-2 3-3 3-3-4.5 1.5-6 4-6 4C10 8 8 9 8 9c1-3 3-4 3-4-5 2-7 9-7 9s1-8 10-9c0 0 7-3 8 5z"/>
            </svg>
          </div>
          <div>
            <h1 className="font-display text-[1.2rem] font-semibold leading-tight tracking-tight text-white">
              Soil Health Intelligence
            </h1>
            <p className="text-[10px] text-forest-400 leading-none mt-0.5 tracking-wide uppercase">
              Agriculture Dept · Govt. of Andhra Pradesh
            </p>
          </div>
        </div>

        {/* Meta info */}
        <div className="hidden md:flex items-center gap-5 text-xs text-forest-400">
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-forest-400 animate-pulse" />
            <span>Krishna District Pilot</span>
          </div>
          <div className="w-px h-3 bg-forest-700" />
          <span>Sentinel-2 L2A · SHC 2025–26</span>
          <div className="w-px h-3 bg-forest-700" />
          <span className="text-forest-300 font-medium">Kharif 2024</span>
        </div>
      </div>
    </nav>
  )
}
