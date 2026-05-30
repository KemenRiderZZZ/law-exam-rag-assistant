# 法考对话前端 2.0

这是当前主用的法考问答前端。

技术栈：

- Vite
- React
- TypeScript

## 主要能力

- 对话式法考问答界面
- 调用本地 `/api/search` 获取引用片段
- 在前端填写模型网关地址、API Key 和模型名
- 支持引用面板、错误提示和设置持久化
- 支持思维导图生成与预览

## 本地启动

```bash
npm install
npm run dev
```

## 构建

```bash
npm run lint
npm run build
```

## 说明

- 这个目录是当前主用版本
- 它不再依赖 Google AI Studio 运行链路
- 搜索接口默认走本地 `/api/*` 代理
- 模型网关配置在浏览器设置里填写，而不是写死在仓库里
