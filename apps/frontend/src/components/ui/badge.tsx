import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 px-2 py-0.5 font-code text-[10px] font-medium uppercase tracking-[0.08em] rounded-sm border transition-colors",
  {
    variants: {
      variant: {
        default:
          "bg-primary/15 text-primary border-primary/40",
        secondary:
          "bg-secondary/15 text-secondary border-secondary/40",
        success:
          "bg-[#10B981]/15 text-[#10B981] border-[#10B981]/40",
        danger:
          "bg-[#EF4444]/15 text-[#EF4444] border-[#EF4444]/40",
        purple:
          "bg-[#8B5CF6]/15 text-[#8B5CF6] border-[#8B5CF6]/40",
        orange:
          "bg-[#F97316]/15 text-[#F97316] border-[#F97316]/40",
        muted:
          "bg-muted text-muted-foreground border-border",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
