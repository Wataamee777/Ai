import os
import discord
import psycopg2
import requests
from app import server

# 環境変数
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

# PostgreSQL接続
def get_db():
    return psycopg2.connect(
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        host=os.environ["PGHOST"],
        port=os.environ.get("PGPORT", "5432")
    )

# テーブル準備
def ensure_table():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS active_channels (
                    guild_id TEXT,
                    channel_id TEXT,
                    PRIMARY KEY (guild_id, channel_id)
                );
            """)
            conn.commit()

ensure_table()

# 操作関数
def is_active(gid, cid):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM active_channels WHERE guild_id=%s AND channel_id=%s", (gid, cid))
            return cur.fetchone() is not None

def activate_channel(gid, cid):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO active_channels (guild_id, channel_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (gid, cid))
            conn.commit()

def deactivate_channel(gid, cid):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM active_channels WHERE guild_id=%s AND channel_id=%s", (gid, cid))
            conn.commit()

# Discord bot設定
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author.bot:
        return

    gid = str(message.guild.id)
    cid = str(message.channel.id)
    content = message.content.strip()

    if content == "/ac":
        if not is_active(gid, cid):
            activate_channel(gid, cid)
            await message.channel.send("✅ このチャンネルをアクティブにしたよ！")
        else:
            await message.channel.send("⚠️ すでにアクティブだよ！")
        return

    if content == "/d-ac":
        if is_active(gid, cid):
            deactivate_channel(gid, cid)
            await message.channel.send("🛑 アクティブを解除したよ！")
        else:
            await message.channel.send("⚠️ もともとアクティブじゃないよ！")
        return

    if content.startswith("/img"):
        prompt = content[4:].strip()
        if not prompt:
            await message.channel.send("🖼️ `/img 猫が空を飛ぶ` みたいに送ってね！")
            return

        await message.channel.send("画像生成中...🧠")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }

        try:
            res = requests.post(url, headers=headers, json=payload).json()
            text = res["candidates"][0]["content"]["parts"][0]["text"]
            await message.channel.send(text)
        except Exception as e:
            print("🧨 Image error:", e)
            await message.channel.send("画像生成中にエラー出ちゃったみたい💥")
        return

    # 自動返信エリア
    if is_active(gid, cid):
        await message.channel.send("考え中...")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": content}]}]
        }

        try:
            res = requests.post(url, headers=headers, json=payload).json()
            text = res["candidates"][0]["content"]["parts"][0]["text"]
            await message.channel.send(text)
        except Exception as e:
            print("🧨 AI error:", e)
            await message.channel.send("エラーが出ちゃったみたい💦")

if __name__ == "__main__":
    server.server_thread()
    client.run(DISCORD_TOKEN)
