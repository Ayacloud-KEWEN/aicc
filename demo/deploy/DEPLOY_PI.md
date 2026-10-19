# 部署到树莓派 5（通过 Tailscale 在手机上演示）

## 工作原理

```
手机（已登录 tailnet）
   │ HTTPS 网页 + 信令：https://<树莓派名>.<tailnet>.ts.net:10051（由 tailscale serve 代理）
   │ 语音 WebRTC/UDP：直接走 Tailscale 的 100.x 地址
   ▼
树莓派 5：server.py（只监听 127.0.0.1:10050）──► Azure Speech / DeepSeek（公网）
```

- 手机浏览器只允许在 **HTTPS**（或 localhost）下使用麦克风。`tailscale serve` 会自动提供有效的 HTTPS 证书，无需自己配置。
- 演示用的手机必须**登录同一个 tailnet**（装 Tailscale App）。语音走 UDP 直连，Tailscale 隧道正好能打通。

## 端口

| 端口 | 用途 | 谁能访问 |
| --- | --- | --- |
| 10050 | AI 点餐服务（server.py） | 只有树莓派本机（127.0.0.1） |
| 10051 | Tailscale 提供的 HTTPS 入口 | 只有你 tailnet 里的设备 |
| 随机 UDP | WebRTC 语音，每通电话临时分配 | 通过 Tailscale 直连，不用手动开 |

想换端口的话，运行脚本时指定：`PORT=10050 SERVE_PORT=10051 bash deploy/setup_pi.sh`。

## 前提

- 树莓派 5，**64 位** Raspberry Pi OS（Bookworm 或更新，Python ≥ 3.11）
- 树莓派和手机都已登录 Tailscale
- 在 Tailscale 管理后台 → **DNS** 页面，打开 **MagicDNS** 和 **HTTPS Certificates**

## 步骤

1. 把 `demo` 文件夹复制到树莓派，例如：

   ```bash
   scp -r demo <用户名>@<树莓派名>:~/aicc-demo
   ```

   不要复制 `data/`，也不要复制 Windows 上的 `.venv`（树莓派会自己装）。`.env` 里有 API Key，可以一起复制，也可以到树莓派上重新填。

2. 在树莓派上编辑 `~/aicc-demo/.env`：填好 Key，并把 STUN 设为空，这样接通更快：

   ```
   STUN_URLS=
   ```

   要演示在线支付，再加上（Stripe 测试模式 Key，见 README“在线支付”一节）：

   ```
   PAYMENT_MODE=stripe
   STRIPE_SECRET_KEY=sk_test_...
   ```

3. 运行安装脚本：

   ```bash
   cd ~/aicc-demo && bash deploy/setup_pi.sh
   ```

   第一次安装依赖大约需要 5–10 分钟。脚本会：安装系统依赖、创建 Python 虚拟环境、注册开机自启服务 `ai-ordering-demo`，并执行 `tailscale serve`。

4. 脚本结束时会打印 `https://<树莓派名>.<tailnet>.ts.net:10051`。在已登录 Tailscale 的手机上打开这个地址即可演示；后厨看板在同一地址加 `/kitchen`。

## 用 GitHub 安装和更新（推荐）

代码在 https://github.com/Ayacloud-KEWEN/aicc ，程序在仓库的 `demo/` 目录里。

**第一次安装**（以 `/mnt/ssd/aicc` 为例）：

```bash
cd /mnt/ssd && git clone https://github.com/Ayacloud-KEWEN/aicc.git
cd /mnt/ssd/aicc/demo
cp .env.example .env    # 填好 Key（或从旧目录复制 .env）
bash deploy/setup_pi.sh
```

**以后更新**（拉取最新代码、装新依赖、重启服务）：

```bash
cd /mnt/ssd/aicc/demo && bash deploy/update_pi.sh
```

`.env` 和 `data/`（订单）不在仓库里，`git pull` 不会覆盖它们。

## 常用命令

```bash
journalctl -u ai-ordering-demo -f       # 实时日志
sudo systemctl restart ai-ordering-demo # 改了代码或 .env 后重启
tailscale serve status                  # 查看 HTTPS 地址
sudo tailscale serve --https=10051 off  # 停止对 tailnet 提供 10051
```

## 注意事项

- **Tailscale 版本**：较早版本的 `tailscale serve` 只允许 443、8443、10000 这几个 HTTPS 端口。如果用 10051 时报错，先升级 Tailscale（`sudo apt update && sudo apt install tailscale`），或者改用 `SERVE_PORT=8443`。

- **客户用自己的手机访问**（不在你的 tailnet 里）：`tailscale funnel` 只能转发 TCP，语音用的 UDP 过不去，需要额外部署一台 TURN 服务器（如 coturn）。这一步还没做，目前请用你自己的手机演示。
- **性能**：树莓派 5 同时处理 1–3 通电话没问题，语音识别、语音合成和大模型都在云端，本机只做语音活动检测和转发。
- **在线支付**：不需要给树莓派开公网端口，也不用配 Stripe webhook。服务器只需要能访问 `api.stripe.com`，付款状态是主动查询的。Stripe 付完款会跳回 `https://<树莓派名>.<tailnet>.ts.net:10051/?paid=…`，所以付款也要在已登录 Tailscale 的手机上完成。已有安装升级时，重新运行一次 `bash deploy/setup_pi.sh` 安装新增的 `stripe` 依赖。
- **网络**：树莓派用网线连接更稳。手机走 4G/5G 也可以，只要 Tailscale 已连接。
- **iPhone**：第一次拨打会询问麦克风权限；如果听不到 AI 的声音，先确认手机没有开静音模式。
