import { describe, expect, it } from "vitest";

import assets from "@/public/data/latest/assets.json";
import {
  projectSpainCoordinate,
  SPAIN_MAINLAND_PATH,
  SPAIN_MAP_VIEWBOX,
  type SpainMapPoint,
} from "@/lib/spain-map";

function parsePathPoints(path: string): SpainMapPoint[] {
  const values = path.match(/-?\d+(?:\.\d+)?/g)?.map(Number) ?? [];
  return Array.from({ length: values.length / 2 }, (_, index) => ({
    x: values[index * 2],
    y: values[index * 2 + 1],
  }));
}

function isInsidePolygon(point: SpainMapPoint, polygon: SpainMapPoint[]) {
  let inside = false;

  for (let current = 0, previous = polygon.length - 1; current < polygon.length; previous = current++) {
    const currentPoint = polygon[current];
    const previousPoint = polygon[previous];
    const crossesLatitude =
      currentPoint.y > point.y !== previousPoint.y > point.y;
    const intersectionX =
      ((previousPoint.x - currentPoint.x) * (point.y - currentPoint.y)) /
        (previousPoint.y - currentPoint.y) +
      currentPoint.x;

    if (crossesLatitude && point.x < intersectionX) {
      inside = !inside;
    }
  }

  return inside;
}

describe("Spain map projection", () => {
  it("projects a known central asset to the expected WGS84 canvas position", () => {
    const point = projectSpainCoordinate(-3.21, 39.39);

    expect(point.x).toBeCloseTo(369.4, 1);
    expect(point.y).toBeCloseTo(311.4, 1);
  });

  it("keeps every portfolio asset inside the mainland outline", () => {
    const outline = parsePathPoints(SPAIN_MAINLAND_PATH);

    for (const asset of assets) {
      const point = projectSpainCoordinate(asset.longitude, asset.latitude);
      expect(isInsidePolygon(point, outline), asset.name).toBe(true);
    }
  });

  it("keeps projected assets within the SVG viewbox", () => {
    for (const asset of assets) {
      const point = projectSpainCoordinate(asset.longitude, asset.latitude);

      expect(point.x).toBeGreaterThan(0);
      expect(point.x).toBeLessThan(SPAIN_MAP_VIEWBOX.width);
      expect(point.y).toBeGreaterThan(0);
      expect(point.y).toBeLessThan(SPAIN_MAP_VIEWBOX.height);
    }
  });
});
