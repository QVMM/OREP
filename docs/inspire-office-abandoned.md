# 启发 Office（ONLYOFFICE）方案 — 已弃用

**状态：** 已弃用（2026-08-06）

## 原因

ONLYOFFICE Docs Community 对白标（去掉品牌 logo / 加载页等）有许可限制，会弹「付费功能」提示；完整去品牌需商业授权。产品决策：**弃用该方案**，相关代码与部署已从仓库移除。

## 已移除内容

- 后端 `/api/inspire-office/**` 与相关 Service / JWT / 空白文档工厂
- 用户端 `/inspire-office` 路由与 AI 应用中心「办公」入口
- Compose `onlyoffice-documentserver`、Nginx `/onlyoffice/` 反代
- 表 `inspire_office_document`（Flyway `V115` 删除；`V114` 保留历史创建记录）

## 后续

已切换为 **Collabora Online + WOPI** 方案，见 `docs/inspire-office-collabora.md`。  
**不得**默认恢复 ONLYOFFICE Community 集成。
