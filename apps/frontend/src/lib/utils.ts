import { type ClassValue, clsx } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

/**
 * Extended tailwind-merge that recognizes our custom font classes
 * (font-heading, font-sans, font-code) as conflicting font-family utilities.
 */
const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-family": [
        "font-heading",
        "font-sans",
        "font-code",
      ],
    },
  },
});

/**
 * Merge Tailwind CSS classes with clsx support.
 * Used by all shadcn/ui components.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
