<div align="center">

# IP Info API

**IP 信息查询接口索引**

收集本机公网 IP、指定 IP 归属地与运营商信息查询接口，方便比较、查阅和接入。

[接口列表](#接口列表) · [最新检测结果](https://github.com/liuheo/ip-info-api/tree/monitor-results) · [使用说明](#使用说明)

</div>

> 本仓库仅整理第三方接口信息，不提供 API 服务。

## 接口列表

<!-- ip-monitor:start -->

[查看最新检测结果：可用状态 / 平均响应 / 成功次数](https://github.com/liuheo/ip-info-api/tree/monitor-results)

> 每 4 小时更新。结果存放于独立分支，首页不保存易过期的检测数值。首次发布前可在 Actions 中查看运行情况。

### 🌐 本机 IP / 指定 IP 均支持

| 接口 | URL | 文档 |
| :--- | :--- | :--- |
| **宝塔** | `https://t.bt.cn/api/v3/ip-lookup` | [查看详情 →](docs/bt-ip-lookup.md) |

### 📍 仅支持本机 IP

| 接口 | URL | 文档 |
| :--- | :--- | :--- |
| **腾讯新闻** | `https://i.news.qq.com/api/ip2city` | [查看详情 →](docs/qq-ip2city.md) |
| **乐视** | `https://g3.letv.com/r` | [查看详情 →](docs/letv-ip.md) |
| **IPIP** | `https://myip.ipip.net/json` | [查看详情 →](docs/ipip-myip.md) |

### 🎯 仅支持指定 IP

| 接口 | URL | 文档 |
| :--- | :--- | :--- |
| **百度** | `https://opendata.baidu.com/api.php` | [查看详情 →](docs/baidu-ip-lookup.md) |

<!-- ip-monitor:end -->

## 使用说明

- **查询范围**：区分本机 IP、指定 IP 与两者均支持，按实际需求选择。
- **可用状态**：每轮检测 5 次，全部成功为可用，部分成功为不稳定，全部失败为不可用；不代表实时状态。
- **平均响应**：预热 1 次后取 5 次检测中成功请求的平均值，基于 GitHub Actions 网络环境，不代表国内访问速度。
- **公网 IP**：指请求出口地址，使用代理或服务端转发时，可能返回代理或服务器 IP。
- **第三方服务**：接口可用性、返回字段及访问限制可能变化，请以服务方实际响应为准。
