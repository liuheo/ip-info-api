[← 返回首页](../README.md)

# 百度 IP 查询

通过指定 IPv4 地址查询归属地和运营商，信息以组合文本返回。

## 接口概览

| 项目 | 内容 |
| :--- | :--- |
| 请求地址 | `https://opendata.baidu.com/api.php` |
| 请求方法 | `GET` |
| 返回格式 | JSON |
| 已验证范围 | 指定 IPv4 地址 |

> 2026-10-13 本地实测返回 HTTP 200 和有效查询结果。尚未验证本机公网 IP 自动查询或 IPv6 支持，暂归入指定 IP 分类。此测试不代表 GitHub Actions 的可用性与响应速度。

## 请求参数

| 参数 | 示例值 | 说明 |
| :--- | :--- | :--- |
| `query` | `110.96.1.1` | 要查询的 IPv4 地址 |
| `resource_id` | `6006` | 本次请求使用的 IP 查询资源编号 |
| `oe` | `utf8` | 本次请求使用的输出编码参数 |
| `co` | 空字符串 | 沿用提供的请求，具体语义与是否必填未验证 |

## 调用示例

以下命令适用于 Bash，URL 需用引号包裹，避免 `&` 被解释为 shell 操作符：

```bash
curl --location 'https://opendata.baidu.com/api.php?co=&resource_id=6006&oe=utf8&query=110.96.1.1'
```

## 返回示例

以下为本地实测响应，非实时数据：

```json
{
  "status": "0",
  "t": "",
  "set_cache_time": "",
  "data": [
    {
      "ExtendedLocation": "",
      "OriginQuery": "110.96.1.1",
      "SchemaVer": "",
      "appinfo": "",
      "disp_type": 0,
      "fetchkey": "110.96.1.1",
      "location": "北京市北京市 铁通",
      "origip": "110.96.1.1",
      "origipquery": "110.96.1.1",
      "resourceid": "6006",
      "role_id": 0,
      "schemaID": "",
      "shareImage": 1,
      "showLikeShare": 1,
      "showlamp": "1",
      "strategyData": {},
      "titlecont": "IP地址查询",
      "tplt": "ip"
    }
  ]
}
```

## 字段与检测说明

- `status`：本次有效响应为字符串 `"0"`，不是数字 `0`。
- `data`：结果数组，读取前应检查是否为空。
- `data[0].origip`：查询的 IP 地址。
- `data[0].location`：归属地和运营商组合文本，本次为 `北京市北京市 铁通`；没有独立的省、市和经纬度字段。
- 定时检测校验 `status`、首条结果的 `origip` 和 `resourceid`，避免把 HTTP 200 但无结果的响应判为可用；不锁定归属地文本，以免正常数据更新导致误报。

接口限流、错误码含义和服务稳定性未取得官方说明，调用方应处理超时、空结果与字段变化。本次请求未使用 API Key，不代表服务方承诺长期匿名开放。
