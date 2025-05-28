import sys
import json
import requests
import re

def call_ollama(prompt, model="phi3"):
    try:
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            }
        )
        # res.json() の結果を直接取得し、"response" キーがあればその値を返す
            # Ollamaの/api/generateエンドポイントのレスポンスは、"response"キーにモデルの出力テキストが含まれる
        full_response = res.json()
        print(f"[DEBUG] Full Ollama Response: {full_response}", file=sys.stderr)
        return full_response.get("response", "") # これがモデルの出力テキスト
    except Exception as e:
        print("[ERROR] ollama 呼び出しに失敗", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return ""

def extract_json_array(text):
    # 最初に現れる JSON 配列（[...]) を抽出
    # JSONが1行で返ってくる場合も考慮し、より柔軟なパターンに
    # '```json\n[...]\n```' のような形式で返される可能性も考慮して調整
    match = re.search(r"```json\s*(\[.*?\])\s*```", text, re.DOTALL)
    if match:
        return match.group(1) # グループ1（括弧内のJSON文字列）を返す
    
    # ```json がない場合でも、直接JSON配列を探す
    match = re.search(r"(\[.*?\])", text, re.DOTALL)
    if match:
        try:
            # 抽出した文字列が実際に有効なJSONであるか検証
            json.loads(match.group(1))
            return match.group(1)
        except json.JSONDecodeError:
            pass # 有効なJSONでなければ次へ

    return "[]" # 見つからない場合は空の配列を返す

def build_prompt(game_state):
    allies = game_state["allies"]
    enemies = game_state["enemies"]

    prompt = (
        "あなたはファイアーエムブレム風の戦術シミュレーションゲームのAIです。\n"
        "以下の敵ユニットと味方ユニットの情報に基づいて、敵ユニットの行動（移動・攻撃）を決定してください。\n"
        "出力は**必ずJSON形式のみ**とし、余計な説明や前後のテキストは一切含めないでください。\n"
        "複数の行動がある場合はJSON配列としてください。\n\n"
    )

    prompt += "### 現在のゲーム状態 ###\n"
    prompt += "敵ユニット:\n"
    for e in enemies:
        prompt += f"- id: {e['id']}, 位置: ({e['x']},{e['y']})\n"

    prompt += "味方ユニット:\n"
    for a in allies:
        prompt += f"- id: {a['id']}, 位置: ({a['x']},{a['y']}), HP: {a['hp']}\n"

    prompt += "\n### 出力形式の指示 ###\n"
    prompt += "以下のようなJSON配列の形式で、敵ユニットの行動を出力してください。**これ以外のテキストは含めないでください。**\n"
    prompt += "例: \n"
    prompt += '```json\n'
    prompt += '[\n'
    prompt += '  {"unit": "enemy1", "action": "move", "to": [6,3]},\n'
    prompt += '  {"unit": "enemy1", "action": "attack", "target": "ally1"}\n'
    prompt += ']\n'
    prompt += '```\n'
    prompt += "\nあなたの回答:\n" # LLMにJSONの出力を促すための最終行

    return prompt

def main():
    print("[DEBUG] main function started.", file=sys.stderr)
    try:
        #input_json = sys.stdin.read()
        json_file_path = r"C:\TR1\TR1_test02\DirectXGame_CG2\DirectXGame\ai_input.json"
        print(f"[DEBUG] Input JSON: {input_json}", file=sys.stderr)

        # ファイルが存在するかチェック
        import os
        if not os.path.exists(json_file_path):
            print(f"[ERROR] Input JSON file not found: {json_file_path}", file=sys.stderr)
            print("[]")# stdout に空のJSONを返し、処理を終了
            return

        with open(json_file_path, 'r', encoding='utf-8') as f: # エンコーディングを明示的に指定
            input_json = f.read()
        
        print(f"[DEBUG] Input JSON (from file): {input_json}", file=sys.stderr) # デバッグ出力変更

        game_state = json.loads(input_json)
        print(f"[DEBUG] Game State: {game_state}", file=sys.stderr)
        print(f"[DEBUG] Type of Game State: {type(game_state)}", file=sys.stderr)

        prompt = build_prompt(game_state)
        print("[DEBUG] Prompt ↓", file=sys.stderr)
        print(prompt, file=sys.stderr)

        print("[DEBUG] Calling ollama...", file=sys.stderr)
        raw_response = call_ollama(prompt)
        print("[DEBUG] LLM raw response ↓", file=sys.stderr)
        print(raw_response, file=sys.stderr)
        
        json_only = extract_json_array(raw_response)
        print("[DEBUG] Extracted JSON ↓", file=sys.stderr)
        print(json_only, file=sys.stderr)

        # 抽出したJSONが空の場合や有効なJSONでない場合は、空の配列を返す
        try:
            parsed_json = json.loads(json_only)
            print(json.dumps(parsed_json)) # 整形してstdoutに返す
        except json.JSONDecodeError:
            print("[]") # 無効なJSONの場合は空の配列を返す
            print(f"[ERROR] Extracted text is not valid JSON: {json_only}", file=sys.stderr)
    
    except json.JSONDecodeError as e:
        print("[]", file=sys.stdout) # 入力JSONが無効な場合
        print(f"[ERROR] JSON Decode Error: {e}", file=sys.stderr) # エラーメッセージをjson.JSONDecodeErrorに変更
    except Exception as e:
        print("[]")  # 応答が無効な場合は空の行動を返す
        # sys.stderr.write(f"[ERROR] {str(e)}\n")
        print(f"[ERROR] An unexpected error occurred: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()