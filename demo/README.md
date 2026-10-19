# AI 语音点餐 Demo（浏览器 IP 通话版）

一个虚构的布列塔尼餐厅 **Restaurant Quimper**（可丽饼、荞麦饼、苹果酒）的网站。访客点击“语音点餐”按钮，在浏览器里直接和 AI 通话（WebRTC），用法语、英语或中文点外带餐、预订座位。订单实时出现在后厨看板上。暂不接入电话号码。

## 组成

| 文件 | 作用 |
| --- | --- |
| `server.py` | FastAPI：网站、后厨看板、订单 API、WebRTC 信令（`/api/offer`） |
| `bot.py` | Pipecat 语音管线：STT → 大模型（工具调用）→ TTS；对话规则和工具 |
| `providers.py` | 按 `.env` 选择服务商：Azure / Deepgram、Azure / ElevenLabs、DeepSeek / Anthropic |
| `payments.py` | Stripe Checkout 在线支付（测试模式）：生成支付链接、向 Stripe 查询付款状态 |
| `restaurant.py` | 三语菜单、购物车、订单与订座（每 30 分钟一个时段，每时段最多 20 人） |
| `static/` | 餐厅首页（`index.html` + `app.js`）、后厨看板（`kitchen.html`） |
| `data/` | 运行后自动生成，保存订单和订座 JSON |

## 运行

1. 把 Key 填进 `demo/.env`（模板见 `.env.example`）。默认组合需要：
   - `AZURE_SPEECH_KEY`、`AZURE_SPEECH_REGION`（建议 `francecentral`）
   - `DEEPSEEK_API_KEY`
2. 启动（在项目根目录 `AICC` 下）：

   ```bash
   .venv/Scripts/python demo/server.py
   ```

3. 打开 http://localhost:7860 ，右上角选语言，点“语音点餐”，允许麦克风。
4. 后厨看板：http://localhost:7860/kitchen

缺 Key 时，页面上会显示黄色提示，列出缺了哪些。

## 切换服务商

在 `.env` 里修改：

```
STT_PROVIDER=deepgram      # 需要 DEEPGRAM_API_KEY
TTS_PROVIDER=elevenlabs    # 需要 ELEVENLABS_API_KEY、ELEVENLABS_VOICE_ID
LLM_PROVIDER=anthropic     # 需要 ANTHROPIC_API_KEY，默认模型 claude-haiku-5-5
```

## 在线支付（Stripe 测试模式）

默认只支持到店付款。要让 AI 提供“现在在线支付”：

1. 注册 Stripe，在 Dashboard 打开 **Test mode**，复制 `sk_test_` 开头的 Secret key。
2. 在 `.env` 里设置：
   ```
   PAYMENT_MODE=stripe
   STRIPE_SECRET_KEY=sk_test_...
   ```
3. 重启服务。

流程：AI 复述订单后问客人“现在网上支付还是到店付款”。选在线支付时，订单先记为“待支付”，通话面板里出现紫色的“支付 €xx”按钮（新标签页打开 Stripe 支付页，通话不中断）。客人付款后：

- 通话页每 3 秒向服务器查询一次，服务器再向 Stripe 查询，按钮变成“已支付 ✓”，AI 会主动道谢；
- Stripe 支付页跳回 `/?paid=…`，页面显示“已付款”的提示；
- 后厨看板显示 **已支付 / 待支付 / 到店付款**。

测试卡号：`4242 4242 4242 4242`，任意未来日期，任意 CVC，不会真实扣款。

卡号只在 Stripe 的页面上输入，本服务器和 AI 都接触不到；AI 被要求绝不在电话里询问卡号。没有用 webhook（树莓派在 Tailscale 内网，Stripe 访问不到），改为主动查询 Stripe。

## 测试话术示例

- 法语：« Bonjour, je voudrais deux galettes complètes avec l'œuf miroir et une bolée de cidre brut à emporter. »
- 英语："Can I book a table for four tomorrow at 8 pm?"
- 中文：“我要一份三文鱼荞麦饼和一个焦糖可丽饼，七点半来拿。”

## 说明与限制

- 每次通话的语言在拨打前选定，通话中途不会切换语音识别语言。
- 在线支付目前只在网页上显示按钮；接入真实电话后，同一个支付链接改为短信发送。
- 已用假 Key 验证过：WebRTC 能接通、开场白能发到页面、Azure 被正常调用（返回 401）。真实语音效果要等填入 Key 后再测。
- 在其他设备上访问时，浏览器只在 `localhost` 或 HTTPS 下允许使用麦克风；局域网演示需要配 HTTPS（或用 ngrok 等隧道）。
