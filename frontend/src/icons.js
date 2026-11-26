// Steps name their icon in Python (`icon = "eye-off"`). Unknown names fall back to a box,
// so a plug-in step never breaks the app.
import {
  AlignVerticalJustifyCenter, Box, ChartColumn, Columns3, Crop, Database, EyeOff, FileCheck, Focus, Frame, Gauge, List, Move, Route, Scan,
  Scissors, Sheet, Shuffle, Spline, Tags, Waves, Zap,
} from "lucide-vue-next";

const icons = {
  "align-vertical": AlignVerticalJustifyCenter, "bar-chart": ChartColumn, box: Box, columns: Columns3, crop: Crop, database: Database,
  "eye-off": EyeOff, "file-check": FileCheck, focus: Focus, frame: Frame, gauge: Gauge, list: List, move: Move, route: Route, scan: Scan,
  scissors: Scissors, sheet: Sheet, shuffle: Shuffle, spline: Spline, tags: Tags, waves: Waves, zap: Zap,
};

export const iconFor = (name) => icons[name] || Box;
