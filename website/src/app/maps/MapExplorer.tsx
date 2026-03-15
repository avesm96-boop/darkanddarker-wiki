"use client";

import styles from "./maps.module.css";

export default function MapExplorer() {
  return (
    <div className={styles.container}>
      <iframe
        src="/maps-viewer/crypt"
        className={styles.viewer}
        title="Crypt Module Map Viewer"
      />
    </div>
  );
}
