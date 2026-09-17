import { cn } from "cn";
import { HugeiconsIcon } from "@hugeicons/react";
import { Loading03Icon } from "@hugeicons/core-free-icons";

function Spinner({
  className,
  strokeWidth = 2,
  ...props
}: React.ComponentProps<"svg">) {
  const iconStrokeWidth =
    typeof strokeWidth === "number" ? strokeWidth : Number(strokeWidth) || 2;

  return (
    <HugeiconsIcon
      icon={Loading03Icon}
      strokeWidth={iconStrokeWidth}
      data-slot="spinner"
      role="status"
      aria-label="Loading"
      className={cn("size-4 animate-spin", className)}
      {...props}
    />
  );
}

export { Spinner };
