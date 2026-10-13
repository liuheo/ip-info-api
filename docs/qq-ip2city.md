[← 返回首页](../README.md)

# 腾讯新闻本机 IP 查询

查询请求出口的公网 IP 及归属地，按本机 IP 查询接口收录。

## 接口概览

| 项目 | 内容 |
| :--- | :--- |
| 请求地址 | `https://i.news.qq.com/api/ip2city` |
| 请求方法 | `GET` |
| 请求参数 | 本次调用不需要参数 |
| 返回格式 | JSON |

## 调用示例

```bash
curl --location 'https://i.news.qq.com/api/ip2city'
```

## 返回示例

接口于 2026-10-13 本地实测返回 HTTP 200。以下仅摘录主要字段，为统一展示而使用 `110.96.1.1` 和北京信息构造格式示例，并非该接口对这个 IP 的实测响应。未验证的地域编码字段不在示例中展示。

```json
{
  "ret": 0,
  "errMsg": "",
  "ip": "110.96.1.1",
  "country": "中国",
  "province": "北京市",
  "city": "北京市",
  "district": "",
  "isp": "",
  "callback": ""
}
```

## 字段与检测说明

- `ret`：实测成功值为数字 `0`，不是字符串 `"0"`。
- `ip`：请求出口的 IP 地址。
- `country`、`province`、`city`：国家、省份、城市。
- `district`、`isp`：本次为空，不应假定必有区县或运营商信息。
- 定时检测要求 `ret == 0` 且 `ip` 为合法 IP，不锁定具体 IP 或归属地。

> 使用代理时结果可能是代理出口，从 GitHub Actions 请求时返回的是 Runner 的出口。浏览器跨域访问受响应头限制：本次 `Access-Control-Allow-Origin` 为 `https://new.qq.com`，不代表任意网站均可直接调用。请求限流、错误码和长期稳定性未取得官方说明。
