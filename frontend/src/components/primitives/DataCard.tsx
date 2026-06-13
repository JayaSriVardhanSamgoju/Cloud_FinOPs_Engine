import { motion } from "framer-motion";
import { ReactNode } from "react";

interface DataCardProps {
  title: string;
  children: ReactNode;
  className?: string;
  accent?: boolean;        // adds a thin accent-colored top border
  span?: "1" | "2" | "3" | "4";  // grid column span for bento layout
}

export function DataCard({ title, children, className = "", accent, span = "1" }: DataCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className={`
        bg-surface-1 border border-border rounded
        hover:border-border-hover transition-colors duration-200
        ${accent ? "border-t-2 border-t-pulse" : ""}
        ${span === "2" ? "md:col-span-2" : ""} 
        ${span === "3" ? "md:col-span-3 lg:col-span-3" : ""}
        ${span === "4" ? "md:col-span-4" : ""}
        p-5 ${className}
      `}
    >
      <h3 className="text-label uppercase text-text-tertiary mb-3">{title}</h3>
      {children}
    </motion.div>
  );
}
