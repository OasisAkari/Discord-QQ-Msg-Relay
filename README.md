# Discord-QQ-Msg-Relay
将Discord和QQ的消息相互转发
# 效果
![Img](https://github.com/Teahouse-Studios/Discord-QQ-Msg-Relay/blob/main/20201117144204.png?raw=true)
# 配置
本项目QQ侧机器人基于[Graia](https://github.com/GraiaProject/Application)，通过[Mirai-API-Http](https://github.com/project-mirai/mirai-api-http)以[mirai](https://github.com/mamoe/mirai)充当无头客户端的形式与主程序交流。
Discord侧以[Discord.py](https://github.com/Rapptz/discord.py)与Discord进行获取信息，以Discord WebHook特性进行发送消息。
以 `Websockets` 库进行信息交换。
你需要先配置好以上环境、获取到Discord的Bot token后继续。
`config.cfg`的内容注解：
```
mah_link= mirai-api-http的链接
qq= 用于充当QQ侧机器人的QQ号。
mah_auth= mirai-api-http的auth token
websocket_port= websocket的端口（自行任意指定一个可用的）
qqgroup= 目标QQ群
webhook_link= Discord目标频道的Webhook链接
dc_channel= Discord目标频道ID
dc_bottoken= Discord Bot token
debug=False
debug_webhook_link=None Discord Debug 频道链接。
```
配置完后，分别启动bot.py和discordbot.py即可
# TODO
- [x] 文字、图片的转发
- [x] 转发内容引用提示
- [ ] Xml/Json 等富文本支持
- [ ] 表情适配
- [x] Embed 消息转发
- [x] 消息撤回
- [ ] 消息编辑
