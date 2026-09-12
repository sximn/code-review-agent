"use client"

import { type ComponentPropsWithRef } from "react"

export function Logo(props: ComponentPropsWithRef<"svg">) {
  return (
    <svg
      className="size-10 fill-black stroke-black dark:fill-neutral-300 dark:stroke-neutral-300"
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 75 500 350"
      {...props}
    >
      <polygon points="0.833 78.913 0.547 201.887 200.666 408.64 220.956 417.13 263.605 417.13 263.788 345.775"></polygon>
      <polygon strokeWidth={1} points="160.735 77.053 160.449 200.027 360.568 406.78 380.858 415.27 423.507 415.27 423.69 343.915"></polygon>
      <path d="M 343.657 151.883 L 343.99 230.101 L 423.438 311.597 C 426.496 182.106 409.07 210.573 496.931 153.849 L 499.453 83.786 L 414.156 82.212 L 343.657 151.883 Z"></path>
    </svg>
  )
}
