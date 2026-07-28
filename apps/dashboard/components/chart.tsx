"use client";

import dynamic from "next/dynamic";
import type { EChartsOption } from "echarts";

const ReactECharts = dynamic(() => import("echarts-for-react"), {
  ssr: false,
  loading: () => <div className="chart-skeleton" aria-hidden="true" />,
});

interface ChartProps {
  option: EChartsOption;
  height?: number;
  ariaLabel: string;
}

export function Chart({ option, height = 300, ariaLabel }: ChartProps) {
  return (
    <div role="img" aria-label={ariaLabel} className="chart-frame">
      <ReactECharts
        option={option}
        notMerge
        lazyUpdate
        style={{ width: "100%", height }}
        opts={{ renderer: "canvas" }}
      />
    </div>
  );
}

export const chartTheme = {
  ink: "#17231f",
  muted: "#6d7671",
  green: "#2f6b55",
  greenSoft: "#91ad9f",
  sand: "#c6a875",
  rust: "#b5663d",
  blue: "#6c8da1",
  line: "#d9ddd8",
  paper: "#fbfaf6",
};

export const baseAxis = {
  axisLine: { lineStyle: { color: chartTheme.line } },
  axisTick: { show: false },
  axisLabel: {
    color: chartTheme.muted,
    fontSize: 10,
    fontFamily: "var(--font-sans)",
  },
  splitLine: { lineStyle: { color: "#e8e9e5", type: "dashed" as const } },
};
