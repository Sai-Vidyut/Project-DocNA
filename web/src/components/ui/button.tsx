import { cn } from "@/lib/utils"
import type { ButtonHTMLAttributes } from "react"

type ButtonVariant = "primary" | "secondary" | "ghost"

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  block?: boolean
  lg?: boolean
}

export function Button({
  className,
  variant = "primary",
  block,
  lg,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        "inline-flex items-center justify-center rounded-md border font-medium transition-colors duration-150",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsla(var(--primary)/0.4)] focus-visible:ring-offset-2 focus-visible:ring-offset-[hsl(var(--background))]",
        "disabled:cursor-not-allowed disabled:opacity-45",
        variant === "primary" &&
          "border-[hsla(var(--primary)/0.3)] bg-[hsl(var(--primary))] text-white hover:bg-[hsl(217_88%_56%)]",
        variant === "secondary" &&
          "glass-1 border-[hsla(var(--foreground)/0.06)] text-[hsl(var(--foreground))] hover:border-[hsla(var(--foreground)/0.1)] hover:bg-[hsla(var(--surface)/0.5)]",
        variant === "ghost" &&
          "border-transparent bg-transparent text-[hsl(var(--muted))] hover:bg-[hsla(var(--foreground)/0.04)] hover:text-[hsl(var(--foreground))]",
        lg ? "px-5 py-2.5 text-[0.925rem]" : "px-3 py-1.5 text-[0.8125rem]",
        block && "w-full",
        className,
      )}
      {...props}
    />
  )
}
