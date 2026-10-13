[← 返回首页](../README.md)

# 宝塔 IP 查询

支持查询本机公网 IP 与指定 IPv4 地址，返回归属地、运营商及经纬度信息。

## 接口概览

| 项目 | 内容 |
| :--- | :--- |
| 请求地址 | `https://t.bt.cn/api/v3/ip-lookup` |
| 请求方法 | `POST` |
| Content-Type | `application/json` |
| 查询范围 | 本机公网 IP / 指定 IPv4 |

## 请求参数

参数通过 JSON 请求体传入。

| 参数 | 示例值 | 说明 |
| :--- | :--- | :--- |
| `target` | `"110.96.1.1"` / `"1"` | 传 IPv4 地址查询指定 IP；传字符串 `"1"` 查询本机公网 IP |

> “本机 IP”指请求出口的公网 IP，使用代理时可能返回代理 IP；从服务端发起请求时，返回的是服务端的出口 IP。

## 调用示例

### 查询指定 IP

以下命令适用于 Bash：

```bash
curl --location 'https://t.bt.cn/api/v3/ip-lookup' \
  --header 'Content-Type: application/json' \
  --data-raw '{"target":"110.96.1.1"}'
```

### 查询本机公网 IP

以下命令适用于 Bash：

```bash
curl --location 'https://t.bt.cn/api/v3/ip-lookup' \
  --header 'Content-Type: application/json' \
  --data-raw '{"target":"1"}'
```

## 返回示例

以下为 2026-10-13 使用统一测试 IP `110.96.1.1` 的本地实测响应，不代表实时查询结果。

```json
{
  "feature": "ip",
  "target": "110.96.1.1",
  "found": true,
  "location": {
    "country": "中国",
    "province": "北京",
    "city": "北京",
    "isp": "中国移动",
    "display": "北京/北京/中国移动",
    "longitude": 116.40529,
    "latitude": 39.904987,
    "has_coordinates": true
  },
  "checked_at": 1791884714,
  "request_id": "b60dff88588771c3101c88b0995ef5d2"
}
```

### 地理信息字段速查

| 字段 | 示例 | 含义 |
| :--- | :--- | :--- |
| `location.country` | `中国` | 国家 |
| `location.province` | `北京` | 省份 |
| `location.city` | `北京` | 城市 |
| `location.isp` | `中国移动` | 运营商或网络提供方 |
| `location.display` | `北京/北京/中国移动` | 组合展示文本 |
| `location.longitude` | `116.40529` | 经度 |
| `location.latitude` | `39.904987` | 纬度 |
| `location.has_coordinates` | `true` | 是否包含坐标 |

> 字段速查基于上述示例整理。错误响应、访问限制及字段完整性尚未记录，接入时请处理请求失败与字段缺失的情况。
