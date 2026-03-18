"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  CartesianGrid,
  ReferenceLine,
  ReferenceDot,
} from "recharts";
import styles from "./stats.module.css";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CurvePoint {
  x: number;
  y: number;
}

interface DerivedStat {
  id: string;
  name: string;
  description: string;
  mechanic?: string;
  unit: string;
  curve: CurvePoint[];
  curve_full: CurvePoint[];
  range: {
    input_min: number;
    input_max: number;
    output_min: number;
    output_max: number;
  };
  baseline: number;
  inverted?: boolean;
}

interface Attribute {
  id: string;
  name: string;
  description: string;
  icon: string;
  derived_stats: DerivedStat[];
  class_base_values: Record<string, number>;
}

interface DefenseCurve {
  name: string;
  description: string;
  input_label: string;
  output_label: string;
  unit: string;
  curve: CurvePoint[];
  curve_full: CurvePoint[];
  range: {
    input_min: number;
    input_max: number;
    output_min: number;
    output_max: number;
  };
}

interface LuckGrade {
  curve: CurvePoint[];
  at_zero: number;
  at_max: number;
}

interface OtherCurve {
  name: string;
  description: string;
  curve: CurvePoint[];
  range?: {
    input_min: number;
    input_max: number;
    output_min: number;
    output_max: number;
  };
}

interface Constants {
  caps: Record<string, number>;
  movement: Record<string, number>;
  hitbox: Record<string, number>;
  health: Record<string, number>;
  spell_recharge: Record<string, number>;
  water: Record<string, number>;
}

interface ClassInfo {
  id: string;
  name: string;
  base_stats: Record<string, number>;
  move_speed: number;
}

interface StatsData {
  version: string;
  generated_at: string;
  data: {
    attributes: Attribute[];
    defense_curves: Record<string, DefenseCurve>;
    luck_grades: {
      description: string;
      grades: Record<string, LuckGrade>;
    };
    other_curves: Record<string, OtherCurve>;
    constants: Constants;
    classes: ClassInfo[];
  };
}

type TabId =
  | "attributes"
  | "calculator"
  | "defense"
  | "hitbox"
  | "luck"
  | "caps";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const ATTR_ICONS: Record<string, string> = {
  strength: "S",
  vigor: "V",
  agility: "A",
  dexterity: "D",
  will: "W",
  knowledge: "K",
  resourcefulness: "R",
};

const ATTR_COLORS: Record<string, string> = {
  strength: "#e04848",
  vigor: "#4caf50",
  agility: "#4488cc",
  dexterity: "#d9bc6a",
  will: "#9b6bdb",
  knowledge: "#4bbfcf",
  resourcefulness: "#e08840",
};

function interpolateCurve(curve: CurvePoint[], x: number): number {
  if (!curve.length) return 0;
  if (x <= curve[0].x) return curve[0].y;
  if (x >= curve[curve.length - 1].x) return curve[curve.length - 1].y;
  for (let i = 0; i < curve.length - 1; i++) {
    if (curve[i].x <= x && x <= curve[i + 1].x) {
      const dx = curve[i + 1].x - curve[i].x;
      if (dx === 0) return curve[i].y;
      const t = (x - curve[i].x) / dx;
      return curve[i].y + t * (curve[i + 1].y - curve[i].y);
    }
  }
  return curve[curve.length - 1].y;
}

function fmtVal(value: number, unit: string): string {
  if (unit === "percent") {
    const pct = value * 100;
    return `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%`;
  }
  if (unit === "multiplier") {
    return `${value.toFixed(2)}x`;
  }
  return value % 1 === 0 ? String(value) : value.toFixed(1);
}

function fmtPercent(value: number): string {
  const pct = value * 100;
  return `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%`;
}

// ---------------------------------------------------------------------------
// Custom Recharts Tooltip
// ---------------------------------------------------------------------------

function CurveTooltip({
  active,
  payload,
  label,
  unit,
}: {
  active?: boolean;
  payload?: { value: number }[];
  label?: number;
  unit: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div
      style={{
        background: "#14110b",
        border: "1px solid rgba(201,168,76,0.3)",
        borderRadius: 2,
        padding: "6px 10px",
        fontSize: "0.75rem",
      }}
    >
      <div style={{ color: "#8a7048", marginBottom: 2 }}>
        Input: {label}
      </div>
      <div style={{ color: "#f0e6cc", fontWeight: 600 }}>
        {fmtVal(payload[0].value, unit)}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatCurveChart({
  data,
  unit,
  baseline,
  classValues,
  attrColors,
  inputLabel,
  outputLabel,
}: {
  data: CurvePoint[];
  unit: string;
  baseline?: number;
  classValues?: { name: string; x: number; color: string }[];
  attrColors?: string;
  inputLabel?: string;
  outputLabel?: string;
}) {
  const yDomain = useMemo(() => {
    const ys = data.map((p) => p.y);
    const min = Math.min(...ys);
    const max = Math.max(...ys);
    const pad = (max - min) * 0.1 || 1;
    return [min - pad, max + pad];
  }, [data]);

  const lineColor = attrColors || "#c9a84c";

  return (
    <div className={styles.chartWrap}>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data} margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(201,168,76,0.06)" />
          <XAxis
            dataKey="x"
            type="number"
            domain={["dataMin", "dataMax"]}
            tick={{ fontSize: 10, fill: "#8a7048" }}
            tickLine={{ stroke: "#4a3a22" }}
            axisLine={{ stroke: "#4a3a22" }}
            label={inputLabel ? { value: inputLabel, position: "bottom", offset: 0, fill: "#4a3a22", fontSize: 10 } : undefined}
          />
          <YAxis
            domain={yDomain}
            tick={{ fontSize: 10, fill: "#8a7048" }}
            tickLine={{ stroke: "#4a3a22" }}
            axisLine={{ stroke: "#4a3a22" }}
            tickFormatter={(v: number) =>
              unit === "percent" ? `${(v * 100).toFixed(0)}%` : String(Math.round(v))
            }
            label={outputLabel ? { value: outputLabel, angle: -90, position: "insideLeft", offset: 10, fill: "#4a3a22", fontSize: 10 } : undefined}
          />
          <RechartsTooltip
            content={<CurveTooltip unit={unit} />}
          />
          {baseline !== undefined && (
            <ReferenceLine
              y={0}
              stroke="rgba(201,168,76,0.15)"
              strokeDasharray="4 4"
            />
          )}
          <ReferenceLine
            x={15}
            stroke="rgba(201,168,76,0.2)"
            strokeDasharray="4 4"
            label={{
              value: "Base 15",
              position: "top",
              fill: "#4a3a22",
              fontSize: 9,
            }}
          />
          <Line
            type="linear"
            dataKey="y"
            stroke={lineColor}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: lineColor, stroke: "#0a0806", strokeWidth: 2 }}
          />
          {classValues?.map((cv) => (
            <ReferenceDot
              key={cv.name}
              x={cv.x}
              y={interpolateCurve(data, cv.x)}
              r={4}
              fill={cv.color}
              stroke="#0a0806"
              strokeWidth={1.5}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
      {/* Chart Legend */}
      {classValues && classValues.length > 0 && (
        <div className={styles.chartLegend}>
          <span className={styles.legendItem}>
            <span className={styles.legendLine} style={{ background: lineColor }} />
            Scaling Curve
          </span>
          {classValues.map((cv) => (
            <span key={cv.name} className={styles.legendItem}>
              <span className={styles.legendDot} style={{ background: cv.color }} />
              {cv.name}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Attribute Section
// ---------------------------------------------------------------------------

function AttributeDetailPanel({
  attr,
  derived,
  selectedDerived,
  setSelectedDerived,
  onClose,
  classDotsForCurve,
  classes,
}: {
  attr: Attribute;
  derived: DerivedStat | undefined;
  selectedDerived: string;
  setSelectedDerived: (id: string) => void;
  onClose: () => void;
  classDotsForCurve: { name: string; x: number; color: string }[];
  classes: ClassInfo[];
}) {
  const panelRef = useCallback((node: HTMLDivElement | null) => {
    if (node) node.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, []);

  // Build formula explanation from curve data
  const formulaInfo = useMemo(() => {
    if (!derived) return null;
    const c = derived.curve_full;
    if (!c.length) return null;
    const inMin = c[0].x;
    const inMax = c[c.length - 1].x;
    const outMin = Math.min(...c.map((p) => p.y));
    const outMax = Math.max(...c.map((p) => p.y));
    const baseVal = derived.baseline;
    const isLinear = c.length === 2;

    return { inMin, inMax, outMin, outMax, baseVal, isLinear, points: c.length };
  }, [derived]);

  return (
    <div className={styles.detailPanel} ref={panelRef}>
      <div className={styles.detailHeader}>
        <h3 className={styles.detailTitle}>
          {attr.name} — Derived Stats
        </h3>
        <button className={styles.closeBtn} onClick={onClose}>
          ✕ Close
        </button>
      </div>

      <div className={styles.derivedTabs}>
        {attr.derived_stats.map((ds) => (
          <button
            key={ds.id}
            className={
              selectedDerived === ds.id
                ? styles.derivedTabActive
                : styles.derivedTab
            }
            onClick={() => setSelectedDerived(ds.id)}
          >
            {ds.name}
          </button>
        ))}
      </div>

      {derived && formulaInfo && (
        <>
          <p className={styles.derivedDesc}>{derived.description}</p>

          {/* Plain-English Mechanic Explanation */}
          {derived.mechanic && (
            <div className={styles.mechanicCallout}>
              <span className={styles.mechanicIcon}>💡</span>
              <p className={styles.mechanicText}>{derived.mechanic}</p>
            </div>
          )}

          {/* Formula & Range Info */}
          <div className={styles.formulaBox}>
            <div className={styles.formulaTitle}>How it works</div>
            <div className={styles.formulaGrid}>
              <div className={styles.formulaItem}>
                <span className={styles.formulaLabel}>Input Range</span>
                <span className={styles.formulaValue}>
                  {formulaInfo.inMin} — {formulaInfo.inMax} {attr.name}
                </span>
              </div>
              <div className={styles.formulaItem}>
                <span className={styles.formulaLabel}>Output Range</span>
                <span className={styles.formulaValue}>
                  {fmtVal(formulaInfo.outMin, derived.unit)} to{" "}
                  {fmtVal(formulaInfo.outMax, derived.unit)}
                </span>
              </div>
              <div className={styles.formulaItem}>
                <span className={styles.formulaLabel}>At Baseline (15)</span>
                <span className={styles.formulaValue}>
                  {fmtVal(formulaInfo.baseVal, derived.unit)}
                </span>
              </div>
              <div className={styles.formulaItem}>
                <span className={styles.formulaLabel}>Scaling</span>
                <span className={styles.formulaValue}>
                  {formulaInfo.isLinear
                    ? "Linear (constant rate)"
                    : `Nonlinear (${formulaInfo.points} data points with interpolation)`}
                </span>
              </div>
            </div>
            <p className={styles.formulaNote}>
              The game uses piecewise linear interpolation between {formulaInfo.points} data
              points defined in the curve table. Values between points are calculated
              proportionally. The chart below shows the exact curve from game files.
            </p>
          </div>

          <StatCurveChart
            data={derived.curve}
            unit={derived.unit}
            baseline={derived.baseline}
            classValues={classDotsForCurve}
            attrColors={ATTR_COLORS[attr.id]}
            inputLabel={`${attr.name} Points`}
            outputLabel={derived.name}
          />

          {/* Class values for this derived stat */}
          <table className={styles.dataTable}>
            <thead>
              <tr>
                <th>Class</th>
                <th>Base {attr.name}</th>
                <th>{derived.name}</th>
              </tr>
            </thead>
            <tbody>
              {classes.map((cls) => {
                const base = attr.class_base_values[cls.id] ?? 15;
                const val = interpolateCurve(derived.curve_full, base);
                return (
                  <tr key={cls.id}>
                    <td>{cls.name}</td>
                    <td>{base}</td>
                    <td>{fmtVal(val, derived.unit)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

function AttributeSection({
  attributes,
  classes,
}: {
  attributes: Attribute[];
  classes: ClassInfo[];
}) {
  const [selectedAttr, setSelectedAttr] = useState<string | null>(null);
  const [selectedDerived, setSelectedDerived] = useState<string>("");

  const attr = attributes.find((a) => a.id === selectedAttr);
  const derived = attr?.derived_stats.find((d) => d.id === selectedDerived);

  const handleAttrClick = useCallback(
    (id: string) => {
      if (selectedAttr === id) {
        setSelectedAttr(null);
        setSelectedDerived("");
      } else {
        setSelectedAttr(id);
        const a = attributes.find((a) => a.id === id);
        setSelectedDerived(a?.derived_stats[0]?.id || "");
      }
    },
    [selectedAttr, attributes]
  );

  const handleClose = useCallback(() => {
    setSelectedAttr(null);
    setSelectedDerived("");
  }, []);

  const maxStatVal = useMemo(() => {
    let mx = 0;
    for (const a of attributes) {
      for (const v of Object.values(a.class_base_values)) {
        if (v > mx) mx = v;
      }
    }
    return mx;
  }, [attributes]);

  // Build class reference dots for curve chart
  const classDotsForCurve = useMemo(() => {
    if (!attr) return [];
    return classes.map((cls, i) => ({
      name: cls.name,
      x: attr.class_base_values[cls.id] ?? 15,
      color: `hsl(${(i * 36) % 360}, 55%, 55%)`,
    }));
  }, [attr, classes]);

  // Group attributes into rows of 2 for inline panel insertion
  const rows: Attribute[][] = [];
  for (let i = 0; i < attributes.length; i += 2) {
    rows.push(attributes.slice(i, i + 2));
  }

  // Find which row the selected attribute is in
  const selectedRowIdx = selectedAttr
    ? rows.findIndex((row) => row.some((a) => a.id === selectedAttr))
    : -1;

  return (
    <div className={styles.section}>
      <h2 className={styles.sectionTitle}>Primary Attributes</h2>
      <p className={styles.sectionDesc}>
        Every character has 7 primary attributes. Click any attribute to explore
        its scaling curves, derived stats, and per-class base values.
      </p>

      {rows.map((row, rowIdx) => (
        <div key={rowIdx}>
          <div className={styles.attrGrid}>
            {row.map((a) => (
              <div
                key={a.id}
                className={
                  selectedAttr === a.id ? styles.attrCardActive : styles.attrCard
                }
                onClick={() => handleAttrClick(a.id)}
              >
                <div className={styles.attrHeader}>
                  <div
                    className={styles.attrIcon}
                    style={{
                      borderColor: ATTR_COLORS[a.id] || "var(--gold-800)",
                      color: ATTR_COLORS[a.id] || "var(--gold-400)",
                    }}
                  >
                    {ATTR_ICONS[a.id] || "?"}
                  </div>
                  <div>
                    <div className={styles.attrName}>{a.name}</div>
                  </div>
                </div>
                <div className={styles.attrDesc}>{a.description}</div>
                <div className={styles.classBarList}>
                  {classes.map((cls) => {
                    const val = a.class_base_values[cls.id] ?? 0;
                    const pct = maxStatVal ? (val / maxStatVal) * 100 : 0;
                    return (
                      <div key={cls.id} className={styles.classBarRow}>
                        <span className={styles.classBarName}>{cls.name}</span>
                        <div className={styles.classBarTrack}>
                          <div
                            className={styles.classBarFill}
                            style={{
                              width: `${pct}%`,
                              background: ATTR_COLORS[a.id] || "var(--gold-600)",
                            }}
                          />
                        </div>
                        <span className={styles.classBarValue}>{val}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>

          {/* Detail panel inserted directly below the row containing the selected attribute */}
          {selectedRowIdx === rowIdx && attr && (
            <AttributeDetailPanel
              attr={attr}
              derived={derived}
              selectedDerived={selectedDerived}
              setSelectedDerived={setSelectedDerived}
              onClose={handleClose}
              classDotsForCurve={classDotsForCurve}
              classes={classes}
            />
          )}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Calculator Section
// ---------------------------------------------------------------------------

function CalculatorSection({
  attributes,
  classes,
}: {
  attributes: Attribute[];
  classes: ClassInfo[];
}) {
  const defaultStats: Record<string, number> = {
    strength: 15,
    vigor: 15,
    agility: 15,
    dexterity: 15,
    will: 15,
    knowledge: 15,
    resourcefulness: 15,
  };

  const [stats, setStats] = useState<Record<string, number>>(defaultStats);

  const updateStat = useCallback((id: string, value: number) => {
    setStats((prev) => ({ ...prev, [id]: value }));
  }, []);

  const applyPreset = useCallback(
    (classId: string) => {
      const cls = classes.find((c) => c.id === classId);
      if (cls) setStats({ ...cls.base_stats });
    },
    [classes]
  );

  // Compute all derived stats from current inputs
  const results = useMemo(() => {
    const output: { group: string; label: string; value: string; tone: string }[] = [];

    for (const attr of attributes) {
      for (const ds of attr.derived_stats) {
        const inputVal = stats[attr.id] ?? 15;
        const val = interpolateCurve(ds.curve_full, inputVal);
        const baseline = ds.baseline;
        let tone = "neutral";
        if (val > baseline + 0.001) tone = "positive";
        else if (val < baseline - 0.001) tone = "negative";

        output.push({
          group: attr.name,
          label: ds.name,
          value: fmtVal(val, ds.unit),
          tone,
        });
      }
    }

    // Add composite stats
    const agiSpeed = interpolateCurve(
      attributes.find((a) => a.id === "agility")?.derived_stats.find((d) => d.id === "move_speed_base")?.curve_full || [],
      stats.agility ?? 15
    );
    output.push({
      group: "Composite",
      label: "Total Move Speed",
      value: `${Math.min(300 + agiSpeed, 330).toFixed(1)}`,
      tone: agiSpeed > 0 ? "positive" : agiSpeed < 0 ? "negative" : "neutral",
    });

    // Max HP
    const maxHp = interpolateCurve(
      attributes.find((a) => a.id === "vigor")?.derived_stats.find((d) => d.id === "max_health_base")?.curve_full || [],
      stats.vigor ?? 15
    );
    output.push({
      group: "Composite",
      label: "Max Health",
      value: `${Math.round(maxHp)} HP`,
      tone: maxHp > 115 ? "positive" : maxHp < 115 ? "negative" : "neutral",
    });

    // Total attribute points
    const totalPts = Object.values(stats).reduce((s, v) => s + v, 0);
    output.push({
      group: "Composite",
      label: "Total Attribute Points",
      value: String(totalPts),
      tone: "neutral",
    });

    return output;
  }, [stats, attributes]);

  // Group results
  const grouped = useMemo(() => {
    const groups: Record<string, typeof results> = {};
    for (const r of results) {
      if (!groups[r.group]) groups[r.group] = [];
      groups[r.group].push(r);
    }
    return groups;
  }, [results]);

  return (
    <div className={styles.section}>
      <h2 className={styles.sectionTitle}>Stat Calculator</h2>
      <p className={styles.sectionDesc}>
        Adjust attribute values to see all derived stats update in real time.
        Use class presets or set custom values.
      </p>
      <div className={styles.calcGrid}>
        <div className={styles.calcInputs}>
          <div className={styles.calcInputsTitle}>Attributes</div>
          {attributes.map((attr) => (
            <div key={attr.id} className={styles.calcRow}>
              <label
                className={styles.calcLabel}
                style={{ color: ATTR_COLORS[attr.id] }}
              >
                {attr.name}
              </label>
              <input
                type="range"
                min={0}
                max={100}
                value={stats[attr.id] ?? 15}
                onChange={(e) =>
                  updateStat(attr.id, parseInt(e.target.value, 10))
                }
                className={styles.calcSlider}
              />
              <span className={styles.calcValue}>{stats[attr.id] ?? 15}</span>
            </div>
          ))}
          <div className={styles.calcPresets}>
            {classes.map((cls) => (
              <button
                key={cls.id}
                className={styles.calcPreset}
                onClick={() => applyPreset(cls.id)}
              >
                {cls.name}
              </button>
            ))}
          </div>
        </div>

        <div className={styles.calcResults}>
          <div className={styles.calcResultsTitle}>Derived Stats</div>
          {Object.entries(grouped).map(([group, items]) => (
            <div key={group} className={styles.resultGroup}>
              <div className={styles.resultGroupLabel}>{group}</div>
              {items.map((item) => (
                <div key={item.label} className={styles.resultRow}>
                  <span className={styles.resultLabel}>{item.label}</span>
                  <span
                    className={`${styles.resultValue} ${
                      item.tone === "positive"
                        ? styles.resultPositive
                        : item.tone === "negative"
                          ? styles.resultNegative
                          : styles.resultNeutral
                    }`}
                  >
                    {item.value}
                  </span>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Defense Section
// ---------------------------------------------------------------------------

function DefenseSection({
  defenseCurves,
}: {
  defenseCurves: Record<string, DefenseCurve>;
}) {
  const [selectedDef, setSelectedDef] = useState<string>("armor_rating");
  const curve = defenseCurves[selectedDef];

  if (!curve) return null;

  // Build a focused view (most relevant range for players)
  const focusedData = useMemo(() => {
    return curve.curve.filter((p) => p.x >= -50 && p.x <= 400);
  }, [curve]);

  const samplePoints = [0, 25, 50, 75, 100, 150, 200, 250, 300, 400];

  return (
    <div className={styles.section}>
      <h2 className={styles.sectionTitle}>Defense Mechanics</h2>
      <p className={styles.sectionDesc}>
        Armor Rating and Magic Resistance convert to damage reduction via
        diminishing-returns curves. Capped at 65% (75% with Defense Mastery / Iron Will).
      </p>
      <div className={styles.derivedTabs}>
        {Object.entries(defenseCurves).map(([key, dc]) => (
          <button
            key={key}
            className={
              selectedDef === key ? styles.derivedTabActive : styles.derivedTab
            }
            onClick={() => setSelectedDef(key)}
          >
            {dc.name}
          </button>
        ))}
      </div>
      <p className={styles.derivedDesc}>{curve.description}</p>
      <StatCurveChart data={focusedData} unit={curve.unit} />
      <table className={styles.dataTable}>
        <thead>
          <tr>
            <th>{curve.input_label}</th>
            <th>{curve.output_label}</th>
          </tr>
        </thead>
        <tbody>
          {samplePoints.map((x) => {
            const y = interpolateCurve(curve.curve_full, x);
            return (
              <tr key={x}>
                <td>{x}</td>
                <td>{fmtPercent(y)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Hitbox Section
// ---------------------------------------------------------------------------

function HitboxSection({ hitbox }: { hitbox: Record<string, number> }) {
  // Game stores hitbox values as percentages (150 = 150%) except defending (0.5 = 50%)
  const entries = [
    { label: "Head", key: "head", pct: hitbox.head, baseline: 100 },
    { label: "Head (Melee)", key: "head_melee", pct: hitbox.head_melee, baseline: 100 },
    { label: "Body", key: "body", pct: hitbox.body, baseline: 100 },
    { label: "Arm", key: "arm", pct: hitbox.arm, baseline: 100 },
    { label: "Hand", key: "hand", pct: hitbox.hand, baseline: 100 },
    { label: "Leg", key: "leg", pct: hitbox.leg, baseline: 100 },
    { label: "Foot", key: "foot", pct: hitbox.foot, baseline: 100 },
    { label: "Defending", key: "defending", pct: hitbox.defending * 100, baseline: 100 },
  ];

  return (
    <div className={styles.section}>
      <h2 className={styles.sectionTitle}>Hitbox Multipliers</h2>
      <p className={styles.sectionDesc}>
        Damage is multiplied based on which body part is hit. Defending (blocking)
        halves incoming damage before other reductions.
      </p>
      <div className={styles.hitboxGrid}>
        {entries.map((e) => {
          return (
            <div key={e.key} className={styles.hitboxItem}>
              <div className={styles.hitboxLabel}>{e.label}</div>
              <div
                className={`${styles.hitboxValue} ${
                  e.pct > 100 ? styles.hitboxHigh : e.pct < 100 ? styles.hitboxLow : ""
                }`}
              >
                {e.pct.toFixed(0)}%
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Luck Section
// ---------------------------------------------------------------------------

function LuckSection({
  luckData,
}: {
  luckData: { description: string; grades: Record<string, LuckGrade> };
}) {
  const [selectedLuck, setSelectedLuck] = useState(0);
  const gradeNames = Object.keys(luckData.grades).sort();

  const gradeInfo: Record<
    string,
    { label: string; short: string; color: string; rarity: string }
  > = {
    LuckGrade00: { label: "Grade 0 — Junk", short: "Junk", color: "#888888", rarity: "Junk" },
    LuckGrade01: { label: "Grade 1 — Poor", short: "Poor", color: "#9d9d9d", rarity: "Poor" },
    LuckGrade02: { label: "Grade 2 — Common", short: "Common", color: "#c8b88a", rarity: "Common" },
    LuckGrade03: { label: "Grade 3 — Standard", short: "Standard", color: "#4caf50", rarity: "Standard" },
    LuckGrade04: { label: "Grade 4 — Uncommon", short: "Uncommon", color: "#66bb6a", rarity: "Uncommon" },
    LuckGrade05: { label: "Grade 5 — Rare", short: "Rare", color: "#42a5f5", rarity: "Rare" },
    LuckGrade06: { label: "Grade 6 — Epic", short: "Epic", color: "#ab47bc", rarity: "Epic" },
    LuckGrade07: { label: "Grade 7 — Legendary", short: "Legendary", color: "#ffa726", rarity: "Legendary" },
    LuckGrade08: { label: "Grade 8 — Unique", short: "Unique", color: "#ef5350", rarity: "Unique" },
  };

  // Build chart data: sample the curves at 0.1 increments from 0-5
  const chartData = useMemo(() => {
    const points: Record<string, number>[] = [];
    for (let luck = 0; luck <= 5; luck += 0.1) {
      const point: Record<string, number> = { luck: Math.round(luck * 10) / 10 };
      for (const gn of gradeNames) {
        const val = interpolateCurve(luckData.grades[gn].curve, luck);
        point[gn] = Math.round(val * 1000) / 10; // as percentage (100 = baseline)
      }
      points.push(point);
    }
    return points;
  }, [luckData, gradeNames]);

  // Compute the multiplier at the selected luck value for each grade
  const selectedValues = useMemo(() => {
    return gradeNames.map((gn) => {
      const val = interpolateCurve(luckData.grades[gn].curve, selectedLuck);
      return { grade: gn, multiplier: val };
    });
  }, [luckData, gradeNames, selectedLuck]);

  return (
    <div className={styles.section}>
      <h2 className={styles.sectionTitle}>Luck & Drop Rates</h2>
      <p className={styles.sectionDesc}>
        Luck shifts which rarity of items you find. More Luck = fewer junk/common
        drops, more rare/epic/legendary drops. The chart shows how each grade&apos;s
        drop weight changes from 0 to 5 Luck.
      </p>

      {/* Interactive Luck Slider */}
      <div className={styles.luckSliderBox}>
        <div className={styles.luckSliderLabel}>
          Your Luck: <strong>{selectedLuck.toFixed(1)}</strong>
        </div>
        <input
          type="range"
          min={0}
          max={50}
          value={selectedLuck * 10}
          onChange={(e) => setSelectedLuck(Number(e.target.value) / 10)}
          className={styles.luckSlider}
        />
        <div className={styles.luckSliderTicks}>
          {[0, 1, 2, 3, 4, 5].map((v) => (
            <span key={v}>{v}</span>
          ))}
        </div>
      </div>

      {/* Drop Weight Cards at Selected Luck */}
      <div className={styles.luckCards}>
        {selectedValues.map(({ grade, multiplier }) => {
          const info = gradeInfo[grade];
          if (!info) return null;
          const pct = ((multiplier - 1) * 100);
          const isUp = multiplier > 1.001;
          const isDown = multiplier < 0.999;
          return (
            <div
              key={grade}
              className={styles.luckCard}
              style={{ borderColor: info.color + "60" }}
            >
              <div className={styles.luckCardDot} style={{ background: info.color }} />
              <div className={styles.luckCardName}>{info.short}</div>
              <div
                className={styles.luckCardValue}
                style={{
                  color: isUp ? "#4caf50" : isDown ? "#e04848" : "var(--text-dim)",
                }}
              >
                {multiplier.toFixed(2)}x
              </div>
              <div
                className={styles.luckCardPct}
                style={{
                  color: isUp ? "#4caf5099" : isDown ? "#e0484899" : "var(--text-muted)",
                }}
              >
                {pct >= 0 ? "+" : ""}{pct.toFixed(1)}%
              </div>
            </div>
          );
        })}
      </div>

      {/* Chart */}
      <div className={styles.chartWrap} style={{ height: 360 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 10, right: 20, bottom: 30, left: 20 }}>
            <CartesianGrid stroke="rgba(201,168,76,0.08)" />
            <XAxis
              dataKey="luck"
              tick={{ fill: "#8a7048", fontSize: 11 }}
              label={{ value: "Luck", position: "bottom", offset: 10, fill: "#8a7048", fontSize: 12 }}
            />
            <YAxis
              tick={{ fill: "#8a7048", fontSize: 11 }}
              label={{ value: "Drop Weight %", angle: -90, position: "insideLeft", offset: -5, fill: "#8a7048", fontSize: 12 }}
              domain={[40, 440]}
            />
            <RechartsTooltip
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null;
                return (
                  <div
                    style={{
                      background: "#14110b",
                      border: "1px solid rgba(201,168,76,0.3)",
                      borderRadius: 2,
                      padding: "8px 12px",
                      fontSize: "0.75rem",
                    }}
                  >
                    <div style={{ color: "#8a7048", marginBottom: 4 }}>
                      Luck: {label}
                    </div>
                    {payload.map((p) => {
                      const info = gradeInfo[p.dataKey as string];
                      if (!info) return null;
                      return (
                        <div key={String(p.dataKey)} style={{ color: info.color, marginBottom: 1 }}>
                          {info.short}: {(Number(p.value) / 100).toFixed(3)}x ({Number(p.value).toFixed(1)}%)
                        </div>
                      );
                    })}
                  </div>
                );
              }}
            />
            <ReferenceLine
              x={selectedLuck}
              stroke="rgba(201,168,76,0.5)"
              strokeDasharray="4 4"
              label={{
                value: `Luck ${selectedLuck.toFixed(1)}`,
                position: "top",
                fill: "#c9a84c",
                fontSize: 11,
              }}
            />
            <ReferenceLine y={100} stroke="rgba(201,168,76,0.15)" />
            {gradeNames.map((gn) => {
              const info = gradeInfo[gn];
              if (!info) return null;
              return (
                <Line
                  key={gn}
                  type="monotone"
                  dataKey={gn}
                  name={info.short}
                  stroke={info.color}
                  strokeWidth={1.5}
                  dot={false}
                  activeDot={{ r: 3 }}
                />
              );
            })}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Chart Legend */}
      <div className={styles.chartLegend}>
        {gradeNames.map((gn) => {
          const info = gradeInfo[gn];
          if (!info) return null;
          return (
            <span key={gn} className={styles.legendItem}>
              <span className={styles.legendDot} style={{ background: info.color }} />
              {info.label}
            </span>
          );
        })}
      </div>

      {/* Data Table */}
      <h3 className={styles.subTitle} style={{ marginTop: 24 }}>
        Drop Weight Table
      </h3>
      <table className={styles.luckTable}>
        <thead>
          <tr>
            <th>Grade</th>
            {[0, 1, 2, 3, 4, 5].map((lv) => (
              <th key={lv}>Luck {lv}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {gradeNames.map((gn) => {
            const grade = luckData.grades[gn];
            const info = gradeInfo[gn];
            return (
              <tr key={gn}>
                <td style={{ color: info?.color }}>{info?.label || gn}</td>
                {[0, 1, 2, 3, 4, 5].map((lv) => {
                  const val = interpolateCurve(grade.curve, lv);
                  const isDecrease = val < 0.999;
                  const isIncrease = val > 1.001;
                  return (
                    <td
                      key={lv}
                      className={
                        isDecrease
                          ? styles.luckDecrease
                          : isIncrease
                            ? styles.luckIncrease
                            : styles.luckNeutral
                      }
                    >
                      {val.toFixed(3)}x
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Caps & Constants Section
// ---------------------------------------------------------------------------

function CapsSection({ constants }: { constants: Constants }) {
  const capLabels: Record<string, string> = {
    max_cooldown_reduction: "Max Cooldown Reduction",
    max_physical_damage_reduction: "Max Physical Damage Reduction",
    max_physical_damage_reduction_defense_mastery: "Max Phys DR (Defense Mastery)",
    max_magical_damage_reduction: "Max Magical Damage Reduction",
    max_magical_damage_reduction_iron_will: "Max Mag DR (Iron Will)",
    max_headshot_damage_mod: "Max Headshot Damage",
    max_projectile_reduction: "Max Projectile Reduction",
    max_spell_casting_speed: "Max Spell Casting Speed",
    min_spell_casting_speed: "Min Spell Casting Speed",
    min_physical_damage_reduction: "Min Physical Damage Reduction",
    min_magical_damage_reduction: "Min Magical Damage Reduction",
    min_debuff_duration_mod: "Min Debuff Duration Mod",
    min_duration_multiplier: "Min Duration Multiplier",
    max_demon_reduction: "Max Demon Reduction",
    max_undead_reduction: "Max Undead Reduction",
  };

  const movLabels: Record<string, string> = {
    base_move_speed: "Base Move Speed",
    max_move_speed: "Max Move Speed",
    stop_threshold: "Stop Movement Threshold",
  };

  const healthLabels: Record<string, string> = {
    recoverable_health_ratio: "Recoverable Health Ratio",
    max_overheal_ratio: "Max Overheal Ratio",
    damage_to_oxygen_ratio: "Damage → Oxygen Ratio",
  };

  const spellLabels: Record<string, string> = {
    default_amount: "Rest Recharge / tick",
    meditation_amount: "Meditation Recharge / tick",
    campfire_amount: "Campfire Recharge / tick",
    clarity_potion_amount: "Clarity Potion Recharge / tick",
    chorale_of_clarity_amount: "Chorale of Clarity / tick",
    required_per_tier: "Recharge Required Per Tier",
    cooldown_reduce_rest: "CD Reduce (Rest) / tick",
    cooldown_reduce_meditation: "CD Reduce (Meditation) / tick",
    cooldown_reduce_campfire: "CD Reduce (Campfire) / tick",
    skill_cooldown_reduce_rest: "Skill CD Reduce (Rest) / tick",
    skill_cooldown_reduce_meditation: "Skill CD Reduce (Meditation) / tick",
    skill_cooldown_reduce_campfire: "Skill CD Reduce (Campfire) / tick",
    campfire_interval: "Campfire Tick Interval (s)",
    normal_rest_interval: "Normal Rest Tick Interval (s)",
  };

  const waterLabels: Record<string, string> = {
    magical_projectile_gravity_ratio: "Magic Projectile Gravity",
    magical_projectile_velocity_ratio: "Magic Projectile Velocity",
    projectile_gravity_ratio: "Projectile Gravity",
    projectile_velocity_ratio: "Projectile Velocity",
    spell_aim_range_ratio: "Spell Aim Range",
  };

  const sections = [
    { title: "Stat Caps & Limits", data: constants.caps, labels: capLabels },
    { title: "Movement", data: constants.movement, labels: movLabels },
    { title: "Health & Recovery", data: constants.health, labels: healthLabels },
    { title: "Spell & Skill Recharge", data: constants.spell_recharge, labels: spellLabels },
    { title: "Water Physics", data: constants.water, labels: waterLabels },
  ];

  function formatConstantVal(key: string, val: number): string {
    // Format caps/percentages nicely
    if (
      key.includes("reduction") ||
      key.includes("duration") ||
      key.includes("cooldown") ||
      key.includes("ratio") ||
      key.includes("speed") && !key.includes("move")
    ) {
      if (Math.abs(val) <= 10) return `${(val * 100).toFixed(0)}%`;
    }
    return val % 1 === 0 ? String(val) : val.toFixed(2);
  }

  return (
    <div className={styles.section}>
      <h2 className={styles.sectionTitle}>Game Constants</h2>
      <p className={styles.sectionDesc}>
        Hard-coded values from game files — caps, limits, thresholds, and physics
        constants that govern combat and mechanics.
      </p>
      <div className={styles.capsGrid}>
        {sections.map((sec) => (
          <div key={sec.title} className={styles.capsCard}>
            <div className={styles.capsCardTitle}>{sec.title}</div>
            {Object.entries(sec.data).map(([key, val]) => (
              <div key={key} className={styles.capsRow}>
                <span className={styles.capsLabel}>
                  {sec.labels[key] || key}
                </span>
                <span className={styles.capsValue}>
                  {formatConstantVal(key, val)}
                </span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

const TABS: { id: TabId; label: string }[] = [
  { id: "attributes", label: "Attributes" },
  { id: "calculator", label: "Calculator" },
  { id: "defense", label: "Defense" },
  { id: "hitbox", label: "Hitbox" },
  { id: "luck", label: "Luck" },
  { id: "caps", label: "Constants" },
];

export default function StatsPage() {
  const [data, setData] = useState<StatsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("attributes");

  useEffect(() => {
    fetch("/data/stats.json")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d: StatsData) => setData(d))
      .catch((e) => setError(e.message));
  }, []);

  if (error) {
    return (
      <main className={styles.page}>
        <div className={styles.error}>Failed to load stats data: {error}</div>
      </main>
    );
  }

  if (!data) {
    return (
      <main className={styles.page}>
        <div className={styles.loading}>Loading stats data...</div>
      </main>
    );
  }

  const { attributes, defense_curves, luck_grades, constants, classes } =
    data.data;

  return (
    <main className={styles.page}>
      <div className={`container ${styles.pageInner}`}>
        <div className="section-head">
          <span className="section-label">Game Data</span>
          <h1 className="section-title">Stats &amp; Attributes</h1>
          <p className="section-desc">
            Complete reference for all attributes, derived stats, scaling curves,
            and game constants — sourced directly from game files.
          </p>
          <div className={styles.headerDivider} />
        </div>

        <div className={styles.tabBar}>
          {TABS.map((t) => (
            <button
              key={t.id}
              className={
                activeTab === t.id ? styles.tabActive : styles.tab
              }
              onClick={() => setActiveTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>

        {activeTab === "attributes" && (
          <AttributeSection attributes={attributes} classes={classes} />
        )}
        {activeTab === "calculator" && (
          <CalculatorSection attributes={attributes} classes={classes} />
        )}
        {activeTab === "defense" && (
          <DefenseSection defenseCurves={defense_curves} />
        )}
        {activeTab === "hitbox" && (
          <HitboxSection hitbox={constants.hitbox} />
        )}
        {activeTab === "luck" && (
          <LuckSection luckData={luck_grades} />
        )}
        {activeTab === "caps" && <CapsSection constants={constants} />}
      </div>
    </main>
  );
}
