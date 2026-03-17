"use client";

import styles from "./itemTooltip.module.css";
import { cleanStatName, formatStatValue } from "./statFormat";

interface Property {
  property_type: string;
  property_value: number;
  is_primary: number;
}

interface Props {
  itemName: string;
  rarity: string;
  properties: Property[];
}

const RARITY_CLASS: Record<string, string> = {
  Poor: styles.rarityPoor,
  Common: styles.rarityCommon,
  Uncommon: styles.rarityUncommon,
  Rare: styles.rarityRare,
  Epic: styles.rarityEpic,
  Legendary: styles.rarityLegendary,
  Unique: styles.rarityUnique,
  Artifact: styles.rarityArtifact,
};

export default function ItemTooltip({ itemName, rarity, properties }: Props) {
  const primary = properties.filter((p) => p.is_primary);
  const secondary = properties.filter((p) => !p.is_primary);
  const rarityClass = RARITY_CLASS[rarity] || styles.rarityCommon;

  return (
    <div className={styles.card}>
      <div className={`${styles.itemName} ${rarityClass}`}>{itemName}</div>
      <div className={`${styles.divider} ${rarityClass}`} />

      <div className={styles.statsSection}>
        {primary.map((p, i) => (
          <div key={i} className={styles.statRow}>
            <span className={styles.dash}>-</span>
            <span className={styles.primaryStat}>
              {cleanStatName(p.property_type)} {formatStatValue(p.property_type, p.property_value)}
            </span>
            <span className={styles.dash}>-</span>
          </div>
        ))}
        {secondary.map((p, i) => (
          <div key={i} className={styles.statRow}>
            <span className={`${styles.dash} ${styles.secondaryDash}`}>-</span>
            <span className={styles.secondaryStat}>
              +{formatStatValue(p.property_type, p.property_value)} {cleanStatName(p.property_type)}
            </span>
            <span className={`${styles.dash} ${styles.secondaryDash}`}>-</span>
          </div>
        ))}
      </div>
    </div>
  );
}
