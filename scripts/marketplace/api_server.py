"""
HTTP API server for marketplace data.

Serves SQLite data to the website, replacing the DarkerDB API dependency.
Runs on the same Hetzner server as the poller.

Endpoints:
  GET /api/v1/listings?item=AdventurerBoots&rarity=&limit=50
  GET /api/v1/prices/history?item=AdventurerBoots&rarity=&hours=168
  GET /api/v1/items?search=boots&limit=30
  GET /api/v1/trending
  GET /api/v1/stats

Usage: python3 api_server.py --port 8080
"""

import asyncio
import json
import logging
import os
import re
import sqlite3
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

sys.path.insert(0, os.path.dirname(__file__))

log = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "market.db")
CATALOG_PATH = os.path.join(os.path.dirname(__file__), "data", "item_catalog.json")

# Load item catalog for search
ITEM_CATALOG = []
if os.path.exists(CATALOG_PATH):
    with open(CATALOG_PATH, encoding="utf-8") as f:
        ITEM_CATALOG = json.load(f)

EQUIPMENT_TYPES = {"Armor", "Weapon", "Accessory"}
MISC_TYPES = {"Misc", "Utility"}
EQUIPMENT_IDS = set()
MISC_IDS = set()
for _item in ITEM_CATALOG:
    mkt_id = _item.get("marketplace_id", "")
    itype = _item.get("item_type", "")
    if itype in EQUIPMENT_TYPES:
        EQUIPMENT_IDS.add(mkt_id)
    elif itype in MISC_TYPES:
        MISC_IDS.add(mkt_id)


def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def get_category_ids(category):
    if category == "equipment":
        return EQUIPMENT_IDS
    elif category == "misc":
        return MISC_IDS
    return None


class MarketAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for marketplace API."""

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        # CORS headers
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

        try:
            if path == "/api/v1/listings":
                result = self.handle_listings(params)
            elif path == "/api/v1/prices/history":
                result = self.handle_price_history(params)
            elif path == "/api/v1/items":
                result = self.handle_items(params)
            elif path == "/api/v1/trending":
                result = self.handle_trending(params)
            elif path == "/api/v1/stats":
                result = self.handle_stats(params)
            elif path == "/api/v1/health":
                result = {"status": "ok", "timestamp": time.time()}
            elif path == "/api/v1/market/activity":
                result = self.handle_market_activity(params)
            elif path == "/api/v1/market/trends":
                result = self.handle_market_trends(params)
            elif path == "/api/v1/market/deals":
                result = self.handle_market_deals(params)
            elif path == "/api/v1/market/fastest":
                result = self.handle_market_fastest(params)
            elif path == "/api/v1/market/volume":
                result = self.handle_market_volume(params)
            elif path == "/api/v1/market/supply":
                result = self.handle_market_supply(params)
            elif path == "/api/v1/market/spreads":
                result = self.handle_market_spreads(params)
            elif path == "/api/v1/rmt/listings":
                result = self.handle_rmt_listings(params)
            elif path == "/api/v1/rmt/sellers":
                result = self.handle_rmt_sellers(params)
            elif path == "/api/v1/rmt/stats":
                result = self.handle_rmt_stats(params)
            else:
                self.send_header("Content-Length", "0")
                self.end_headers()
                return

            body = json.dumps(result, default=str).encode()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        except Exception as e:
            log.error(f"Request error: {e}")
            error_body = json.dumps({"error": "Internal server error"}).encode()
            self.send_header("Content-Length", str(len(error_body)))
            self.end_headers()
            self.wfile.write(error_body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress default logging

    # ── Endpoint Handlers ────────────────────────────────────

    def handle_listings(self, params):
        """GET /api/v1/listings?item=AdventurerBoots&base_rarity=Epic&limit=50&status=active&sort=price_asc"""
        db = get_db()
        item = params.get("item", "")
        rarity = params.get("rarity", "")
        base_rarity = params.get("base_rarity", "")
        limit = min(int(params.get("limit", "50")), 500)
        status = params.get("status", "active")
        sort = params.get("sort", "price_asc")

        query = "SELECT * FROM listings WHERE 1=1"
        args = []

        if item:
            mkt_id = item if item.startswith("Id.Item.") else f"Id.Item.{item}"
            query += " AND item_marketplace_id = ?"
            args.append(mkt_id)

        if rarity:
            if rarity.isdigit():
                query += " AND rarity = ?"
                args.append(int(rarity))
            else:
                query += " AND rarity_name = ?"
                args.append(rarity)

        if base_rarity:
            query += " AND base_rarity = ?"
            args.append(base_rarity)

        if status:
            query += " AND status = ?"
            args.append(status)

        sort_map = {
            "price_asc": "price ASC",
            "price_desc": "price DESC",
            "sold_desc": "sold_at DESC",
            "newest": "first_seen_at DESC",
        }
        query += f" ORDER BY {sort_map.get(sort, 'price ASC')} LIMIT ?"
        args.append(limit)

        rows = db.execute(query, args).fetchall()

        # Fetch properties for each listing, strip sensitive fields
        STRIP_FIELDS = {"seller_info", "first_seen_poll_id", "last_seen_poll_id",
                        "item_unique_id", "item_id", "slot_count", "rarity_tier", "listing_time"}
        listings = []
        for row in rows:
            listing = {k: v for k, v in dict(row).items() if k not in STRIP_FIELDS}
            qty = max(listing.get("item_count", 1), 1)
            listing["price_per_unit"] = round(listing["price"] / qty, 1)
            props = db.execute(
                "SELECT property_type, property_value, is_primary FROM listing_properties WHERE listing_id=?",
                (row["listing_id"],)
            ).fetchall()
            listing["properties"] = [dict(p) for p in props]
            listings.append(listing)

        db.close()
        return {"listings": listings, "count": len(listings)}

    def handle_price_history(self, params):
        """GET /api/v1/prices/history?item=AdventurerBoots&rarity=&hours=168"""
        db = get_db()
        item = params.get("item", "")
        rarity = params.get("rarity", "")
        hours = int(params.get("hours", "168"))  # default 7 days

        if not item:
            return {"error": "item parameter required"}

        mkt_id = item if item.startswith("Id.Item.") else f"Id.Item.{item}"
        cutoff = time.time() - (hours * 3600)

        query = """
            SELECT timestamp, active_count, min_price, max_price,
                   median_price, avg_price, p10_price, p25_price, p75_price, p90_price
            FROM price_snapshots
            WHERE item_marketplace_id = ? AND timestamp > ?
        """
        args = [mkt_id, cutoff]

        if rarity:
            query += " AND rarity = ?"
            args.append(int(rarity))

        query += " ORDER BY timestamp ASC"
        rows = db.execute(query, args).fetchall()
        db.close()

        return {"history": [dict(r) for r in rows], "count": len(rows)}

    def handle_items(self, params):
        """GET /api/v1/items?search=boots&limit=30"""
        search = params.get("search", "").lower()
        limit = int(params.get("limit", "30"))

        if not search:
            return {"items": [], "count": 0}

        results = []
        for item in ITEM_CATALOG:
            name = item.get("name", "")
            mkt_id = item.get("marketplace_id", "")
            if search in name.lower() or search in mkt_id.lower():
                results.append(item)
                if len(results) >= limit:
                    break

        return {"items": results, "count": len(results)}

    def handle_trending(self, params):
        """GET /api/v1/trending — returns items with most listings + RMT-clean price data"""
        db = get_db()

        # Get items with most active listings — unfiltered prices (all listings)
        # RMT detection runs in background for analysis, but user-facing data shows everything
        rows = db.execute("""
            SELECT item_marketplace_id, item_base_name,
                   SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) as listing_count,
                   MIN(CASE WHEN status='active' THEN CAST(price AS REAL) / MAX(item_count, 1) END) as min_price,
                   MAX(CASE WHEN status='active' THEN CAST(price AS REAL) / MAX(item_count, 1) END) as max_price,
                   AVG(CASE WHEN status='active' THEN CAST(price AS REAL) / MAX(item_count, 1) END) as avg_price,
                   SUM(CASE WHEN status='sold' THEN 1 ELSE 0 END) as sold_count
            FROM listings
            GROUP BY item_marketplace_id
            HAVING listing_count > 0
            ORDER BY listing_count DESC
            LIMIT 50
        """).fetchall()

        items = []
        for row in rows:
            mkt_id = row["item_marketplace_id"]

            # Get recent price snapshots for sparkline
            snapshots = db.execute("""
                SELECT timestamp, avg_price, min_price, max_price, active_count
                FROM price_snapshots
                WHERE item_marketplace_id = ?
                ORDER BY timestamp DESC LIMIT 20
            """, (mkt_id,)).fetchall()

            items.append({
                "marketplace_id": mkt_id,
                "name": row["item_base_name"],
                "active_count": row["listing_count"],
                "sold_count": row["sold_count"],
                "min_price": row["min_price"],
                "max_price": row["max_price"],
                "avg_price": round(row["avg_price"], 1) if row["avg_price"] else 0,
                "price_history": [dict(s) for s in reversed(snapshots)],
            })

        db.close()
        return {"items": items, "count": len(items)}

    def handle_stats(self, params):
        """GET /api/v1/stats — database statistics"""
        db = get_db()
        stats = {
            "total_listings": db.execute("SELECT COUNT(*) FROM listings").fetchone()[0],
            "active_listings": db.execute("SELECT COUNT(*) FROM listings WHERE status='active'").fetchone()[0],
            "sold_listings": db.execute("SELECT COUNT(*) FROM listings WHERE status='sold'").fetchone()[0],
            "unique_items": db.execute("SELECT COUNT(DISTINCT item_marketplace_id) FROM listings").fetchone()[0],
            "poll_sessions": db.execute("SELECT COUNT(*) FROM poll_sessions").fetchone()[0],
            "price_snapshots": db.execute("SELECT COUNT(*) FROM price_snapshots").fetchone()[0],
        }

        # Last poll info — only expose timing, not internal details
        last_poll = db.execute(
            "SELECT started_at, finished_at, status FROM poll_sessions ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if last_poll:
            stats["last_poll"] = {"status": last_poll["status"]}

        # Most recent data update (from either fast or full scanner)
        latest = db.execute(
            "SELECT MAX(last_seen_at) as ts FROM listings WHERE status='active'"
        ).fetchone()
        if latest and latest["ts"]:
            stats["last_data_at"] = latest["ts"]

        db.close()
        return stats

    def handle_market_activity(self, params):
        """GET /api/v1/market/activity?days=14 — daily listed vs sold totals"""
        db = get_db()
        days = min(int(params.get("days", "14")), 90)
        cutoff = time.time() - (days * 86400)

        rows = db.execute("""
            SELECT
                CAST(started_at / 86400 AS INTEGER) * 86400 as day_ts,
                SUM(COALESCE(listings_new, 0)) as listed,
                SUM(COALESCE(listings_sold, 0)) as sold
            FROM poll_sessions
            WHERE started_at > ? AND status = 'completed'
            GROUP BY CAST(started_at / 86400 AS INTEGER)
            ORDER BY day_ts ASC
        """, (cutoff,)).fetchall()

        db.close()
        return {"buckets": [dict(r) for r in rows], "count": len(rows)}

    def handle_market_trends(self, params):
        """GET /api/v1/market/trends?hours=24 — top rising/falling items by min price change"""
        db = get_db()
        hours = min(int(params.get("hours", "24")), 168)
        category = params.get("category", "")
        cat_ids = get_category_ids(category)
        now = time.time()

        # Get latest min_price per item (most recent snapshot)
        # and the min_price from ~hours ago, compute change
        rows = db.execute("""
            WITH current AS (
                SELECT item_marketplace_id, min_price, active_count, timestamp,
                       ROW_NUMBER() OVER (PARTITION BY item_marketplace_id ORDER BY timestamp DESC) as rn
                FROM price_snapshots
                WHERE timestamp > ? AND active_count >= 3 AND min_price > 0
            ),
            previous AS (
                SELECT item_marketplace_id, min_price, timestamp,
                       ROW_NUMBER() OVER (PARTITION BY item_marketplace_id ORDER BY timestamp DESC) as rn
                FROM price_snapshots
                WHERE timestamp BETWEEN ? AND ? AND active_count >= 3 AND min_price > 0
            )
            SELECT c.item_marketplace_id,
                   c.min_price as current_min,
                   c.active_count,
                   p.min_price as previous_min,
                   ROUND((c.min_price - p.min_price) * 100.0 / p.min_price, 1) as change_pct
            FROM current c
            JOIN previous p ON c.item_marketplace_id = p.item_marketplace_id AND p.rn = 1
            WHERE c.rn = 1
            ORDER BY change_pct ASC
        """, (now - 3600, now - hours * 3600 - 1800, now - hours * 3600 + 1800)).fetchall()

        all_items = [dict(r) for r in rows]

        # Get item names from listings table
        names = {}
        for item in all_items:
            mkt_id = item["item_marketplace_id"]
            if mkt_id not in names:
                row = db.execute(
                    "SELECT item_base_name FROM listings WHERE item_marketplace_id = ? LIMIT 1",
                    (mkt_id,)
                ).fetchone()
                names[mkt_id] = row["item_base_name"] if row else mkt_id.replace("Id.Item.", "")

        for item in all_items:
            item["name"] = names[item["item_marketplace_id"]]

        db.close()

        if cat_ids:
            all_items = [i for i in all_items if i["item_marketplace_id"] in cat_ids]
        falling = [i for i in all_items if i["change_pct"] < 0][:10]
        rising = [i for i in reversed(all_items) if i["change_pct"] > 0][:10]

        return {"falling": falling, "rising": rising}

    def handle_market_deals(self, params):
        """GET /api/v1/market/deals — underpriced active listings"""
        db = get_db()
        limit = min(int(params.get("limit", "10")), 50)
        category = params.get("category", "")
        cat_ids = get_category_ids(category)
        try:
            rows = db.execute("""
                SELECT l.listing_id, l.item_marketplace_id, l.item_base_name,
                       l.base_rarity, l.price, l.item_count,
                       r.fair_value, r.price_ratio, r.model_type
                FROM listings l
                JOIN gold_listing_rmt_scores r ON l.listing_id = r.listing_id
                WHERE l.status = 'active' AND r.hard_flag = 0
                  AND r.fair_value > 0 AND r.price_ratio < 0.7 AND r.price_ratio > 0
                ORDER BY r.price_ratio ASC LIMIT 200
            """).fetchall()
            items = [dict(r) for r in rows]
            if cat_ids:
                items = [i for i in items if i["item_marketplace_id"] in cat_ids]
            items = items[:limit]
            for item in items:
                item["discount_pct"] = round((1 - item["price_ratio"]) * 100, 1)
                item["price_per_unit"] = round(item["price"] / max(item["item_count"], 1), 1)
            return {"deals": items, "count": len(items)}
        except sqlite3.OperationalError:
            return {"deals": [], "count": 0, "note": "Fair value models not ready"}
        finally:
            db.close()

    def handle_market_fastest(self, params):
        """GET /api/v1/market/fastest — fastest selling items"""
        db = get_db()
        hours = min(int(params.get("hours", "24")), 168)
        category = params.get("category", "")
        cat_ids = get_category_ids(category)
        cutoff = time.time() - hours * 3600
        rows = db.execute("""
            SELECT item_marketplace_id, item_base_name,
                   COUNT(*) as sold_count,
                   AVG(sold_at - first_seen_at) as avg_time_to_sell,
                   AVG(CAST(price AS REAL) / MAX(item_count, 1)) as avg_price
            FROM listings
            WHERE status = 'sold' AND sold_at > ? AND sold_at > first_seen_at
            GROUP BY item_marketplace_id
            HAVING sold_count >= 3
            ORDER BY avg_time_to_sell ASC LIMIT 100
        """, (cutoff,)).fetchall()
        items = [dict(r) for r in rows]
        if cat_ids:
            items = [i for i in items if i["item_marketplace_id"] in cat_ids]
        items = items[:10]
        for item in items:
            row = db.execute("SELECT COUNT(*) as c FROM listings WHERE item_marketplace_id = ? AND status = 'active'", (item["item_marketplace_id"],)).fetchone()
            item["active_count"] = row["c"] if row else 0
            item["avg_time_to_sell"] = round(item["avg_time_to_sell"])
            item["avg_price"] = round(item["avg_price"])
        db.close()
        return {"items": items, "count": len(items)}

    def handle_market_volume(self, params):
        """GET /api/v1/market/volume — most traded items by sale count"""
        db = get_db()
        hours = min(int(params.get("hours", "24")), 168)
        category = params.get("category", "")
        cat_ids = get_category_ids(category)
        cutoff = time.time() - hours * 3600
        rows = db.execute("""
            SELECT item_marketplace_id, item_base_name,
                   COUNT(*) as sold_count,
                   SUM(price) as total_gold,
                   AVG(CAST(price AS REAL) / MAX(item_count, 1)) as avg_price
            FROM listings
            WHERE status = 'sold' AND sold_at > ?
            GROUP BY item_marketplace_id
            HAVING sold_count >= 2
            ORDER BY sold_count DESC LIMIT 100
        """, (cutoff,)).fetchall()
        items = [dict(r) for r in rows]
        if cat_ids:
            items = [i for i in items if i["item_marketplace_id"] in cat_ids]
        items = items[:10]
        for item in items:
            row = db.execute("SELECT COUNT(*) as c FROM listings WHERE item_marketplace_id = ? AND status = 'active'", (item["item_marketplace_id"],)).fetchone()
            item["active_count"] = row["c"] if row else 0
            item["avg_price"] = round(item["avg_price"])
        db.close()
        return {"items": items, "count": len(items)}

    def handle_market_supply(self, params):
        """GET /api/v1/market/supply — items with biggest supply changes"""
        db = get_db()
        hours = min(int(params.get("hours", "24")), 168)
        category = params.get("category", "")
        cat_ids = get_category_ids(category)
        now = time.time()
        rows = db.execute("""
            WITH current AS (
                SELECT item_marketplace_id, active_count, min_price,
                       ROW_NUMBER() OVER (PARTITION BY item_marketplace_id ORDER BY timestamp DESC) as rn
                FROM price_snapshots WHERE timestamp > ? AND active_count >= 3
            ),
            previous AS (
                SELECT item_marketplace_id, active_count,
                       ROW_NUMBER() OVER (PARTITION BY item_marketplace_id ORDER BY timestamp DESC) as rn
                FROM price_snapshots WHERE timestamp BETWEEN ? AND ? AND active_count >= 3
            )
            SELECT c.item_marketplace_id, c.active_count as current_count, c.min_price,
                   p.active_count as previous_count,
                   c.active_count - p.active_count as change,
                   ROUND((c.active_count - p.active_count) * 100.0 / MAX(p.active_count, 1), 1) as change_pct
            FROM current c
            JOIN previous p ON c.item_marketplace_id = p.item_marketplace_id AND p.rn = 1
            WHERE c.rn = 1 AND ABS(c.active_count - p.active_count) >= 2
            ORDER BY change_pct ASC
        """, (now - 3600, now - hours * 3600 - 1800, now - hours * 3600 + 1800)).fetchall()
        all_items = [dict(r) for r in rows]
        names = {}
        for item in all_items:
            mkt_id = item["item_marketplace_id"]
            if mkt_id not in names:
                row = db.execute("SELECT item_base_name FROM listings WHERE item_marketplace_id = ? LIMIT 1", (mkt_id,)).fetchone()
                names[mkt_id] = row["item_base_name"] if row else mkt_id.replace("Id.Item.", "")
        for item in all_items:
            item["name"] = names[item["item_marketplace_id"]]
        if cat_ids:
            all_items = [i for i in all_items if i["item_marketplace_id"] in cat_ids]
        db.close()
        draining = [i for i in all_items if i["change"] < 0][:10]
        flooding = [i for i in reversed(all_items) if i["change"] > 0][:10]
        return {"draining": draining, "flooding": flooding}

    def handle_market_spreads(self, params):
        """GET /api/v1/market/spreads — items with biggest min-to-median price spread"""
        db = get_db()
        category = params.get("category", "")
        cat_ids = get_category_ids(category)
        rows = db.execute("""
            SELECT item_marketplace_id, active_count, min_price, median_price,
                   median_price - min_price as spread,
                   ROUND((median_price - min_price) * 100.0 / MAX(min_price, 1), 1) as spread_pct,
                   ROW_NUMBER() OVER (PARTITION BY item_marketplace_id ORDER BY timestamp DESC) as rn
            FROM price_snapshots
            WHERE active_count >= 10 AND min_price > 0 AND median_price > min_price
        """).fetchall()
        items = [dict(r) for r in rows if r["rn"] == 1]
        names = {}
        for item in items:
            mkt_id = item["item_marketplace_id"]
            if mkt_id not in names:
                row = db.execute("SELECT item_base_name FROM listings WHERE item_marketplace_id = ? LIMIT 1", (mkt_id,)).fetchone()
                names[mkt_id] = row["item_base_name"] if row else mkt_id.replace("Id.Item.", "")
        for item in items:
            item["name"] = names[item["item_marketplace_id"]]
            del item["rn"]
        if cat_ids:
            items = [i for i in items if i["item_marketplace_id"] in cat_ids]
        items.sort(key=lambda x: x["spread_pct"], reverse=True)
        items = items[:10]
        db.close()
        return {"items": items, "count": len(items)}

    # ── RMT Endpoints ─────────────────────────────────────────

    def handle_rmt_listings(self, params):
        """GET /api/v1/rmt/listings?item=&limit=50 — hard-flagged listings"""
        db = get_db()
        try:
            item = params.get("item", "")
            limit = int(params.get("limit", "50"))

            query = """
                SELECT l.*, r.fair_value, r.price_ratio, r.model_type as rmt_model,
                       r.soft_flag, r.hard_flag
                FROM listings l
                JOIN gold_listing_rmt_scores r ON l.listing_id = r.listing_id
                WHERE r.hard_flag = 1 AND l.status = 'active'
            """
            args = []

            if item:
                mkt_id = item if item.startswith("Id.Item.") else f"Id.Item.{item}"
                query += " AND l.item_marketplace_id = ?"
                args.append(mkt_id)

            query += " ORDER BY r.price_ratio DESC LIMIT ?"
            args.append(limit)

            rows = db.execute(query, args).fetchall()
            listings = []
            for row in rows:
                listing = dict(row)
                listing["price_per_unit"] = round(listing["price"] / max(listing.get("item_count", 1), 1), 1)
                props = db.execute(
                    "SELECT property_type, property_value, is_primary FROM listing_properties WHERE listing_id=?",
                    (row["listing_id"],)
                ).fetchall()
                listing["properties"] = [dict(p) for p in props]
                listings.append(listing)

            return {"listings": listings, "count": len(listings)}
        except sqlite3.OperationalError:
            return {"listings": [], "count": 0, "note": "RMT tables not initialized yet"}
        finally:
            db.close()

    def handle_rmt_sellers(self, params):
        """GET /api/v1/rmt/sellers?limit=30 — flagged sellers"""
        db = get_db()
        try:
            limit = int(params.get("limit", "30"))
            rows = db.execute("""
                SELECT * FROM gold_seller_scores
                WHERE seller_flag = 1 AND active_listings > 0
                ORDER BY flag_rate DESC, flagged_hard DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return {"sellers": [dict(r) for r in rows], "count": len(rows)}
        except sqlite3.OperationalError:
            return {"sellers": [], "count": 0, "note": "RMT tables not initialized yet"}
        finally:
            db.close()

    def handle_rmt_stats(self, params):
        """GET /api/v1/rmt/stats — overview stats"""
        db = get_db()
        try:
            stats = {}
            stats["total_scored"] = db.execute(
                "SELECT COUNT(*) FROM gold_listing_rmt_scores"
            ).fetchone()[0]
            stats["soft_flagged"] = db.execute(
                "SELECT COUNT(*) FROM gold_listing_rmt_scores WHERE soft_flag = 1"
            ).fetchone()[0]
            stats["hard_flagged"] = db.execute(
                "SELECT COUNT(*) FROM gold_listing_rmt_scores WHERE hard_flag = 1"
            ).fetchone()[0]
            stats["estimated_rmt_gold"] = db.execute(
                "SELECT COALESCE(SUM(l.price), 0) FROM listings l "
                "JOIN gold_listing_rmt_scores r ON l.listing_id = r.listing_id "
                "WHERE r.hard_flag = 1 AND l.status = 'active'"
            ).fetchone()[0]
            stats["flagged_sellers"] = db.execute(
                "SELECT COUNT(*) FROM gold_seller_scores WHERE seller_flag = 1"
            ).fetchone()[0]
            stats["models_count"] = db.execute(
                "SELECT COUNT(*) FROM gold_fair_value_models"
            ).fetchone()[0]
            stats["regression_models"] = db.execute(
                "SELECT COUNT(*) FROM gold_fair_value_models WHERE model_type = 'regression'"
            ).fetchone()[0]

            # Top 10 items by hard-flagged count
            top_items = db.execute("""
                SELECT l.item_base_name, l.item_marketplace_id, COUNT(*) as flagged_count,
                       SUM(l.price) as total_rmt_gold
                FROM listings l
                JOIN gold_listing_rmt_scores r ON l.listing_id = r.listing_id
                WHERE r.hard_flag = 1 AND l.status = 'active'
                GROUP BY l.item_marketplace_id
                ORDER BY flagged_count DESC LIMIT 10
            """).fetchall()
            stats["top_rmt_items"] = [dict(r) for r in top_items]

            return stats
        except sqlite3.OperationalError:
            return {"total_scored": 0, "soft_flagged": 0, "hard_flagged": 0,
                    "note": "RMT tables not initialized yet"}
        finally:
            db.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Marketplace API Server")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    server = HTTPServer((args.host, args.port), MarketAPIHandler)
    log.info(f"API server running on http://{args.host}:{args.port}")
    log.info(f"Database: {DB_PATH}")
    log.info(f"Catalog: {len(ITEM_CATALOG)} items")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Stopped")


if __name__ == "__main__":
    main()
