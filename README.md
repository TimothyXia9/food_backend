# 卡路里追踪应用 (Calorie Tracker App)

一个基于 React + TypeScript 的现代化健康管理应用，帮助用户跟踪每日卡路里摄入量和营养数据。

## ✨ 主要功能

### 🔐 用户认证

-   登录/注册系统
-   表单验证
-   用户会话管理

### 📊 卡路里追踪

-   每日卡路里目标设置和监控
-   实时进度显示
-   营养成分分解（蛋白质、脂肪、碳水化合物、纤维）

### 🔍 食物搜索与管理

-   丰富的食物数据库
-   智能搜索功能
-   自定义食物添加
-   分量计算器

### 📈 统计分析

-   可视化图表展示
-   多维度数据分析（周/月/年）
-   营养趋势追踪
-   成就徽章系统

### 👤 个人资料管理

-   个人信息编辑
-   BMI 计算器
-   健康指标监控
-   目标设置

## 🛠️ 技术栈

-   **前端框架**: React 18.2.0
-   **类型系统**: TypeScript 4.9.5
-   **构建工具**: Create React App
-   **样式方案**: Styled-JSX
-   **代码规范**: ESLint + TypeScript ESLint
-   **测试框架**: Jest + React Testing Library

## 📁 项目结构

```
src/
├── App.tsx                 # 主应用组件
├── App.css                 # 全局样式
├── components/             # 可复用组件
│   └── Navigation.tsx      # 导航栏组件
├── pages/                  # 页面组件
│   ├── LoginPage.tsx       # 登录页面
│   ├── Dashboard.tsx       # 首页仪表板
│   ├── FoodSearch.tsx      # 食物搜索页面
│   ├── Profile.tsx         # 个人资料页面
│   └── Statistics.tsx      # 统计分析页面
└── types/                  # TypeScript 类型定义
    └── styled-jsx.d.ts     # Styled-JSX 类型扩展
```

## 🚀 快速开始

### 环境要求

-   Node.js >= 16.0.0
-   npm >= 8.0.0

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm start
```

应用将在 http://localhost:3000 启动

### 构建生产版本

```bash
npm run build
```

### 类型检查

```bash
npm run type-check
```

### 代码检查

```bash
npm run lint
npm run lint:fix  # 自动修复
```

## 📱 界面预览

### 🏠 首页仪表板

-   每日卡路里进度条
-   营养成分饼图
-   最近添加的食物
-   快捷操作按钮

### 🍎 食物搜索

-   实时搜索建议
-   详细营养信息
-   分量自定义
-   收藏功能

### 📊 统计分析

-   交互式图表
-   时间范围选择
-   营养趋势分析
-   达成情况统计

### 👤 个人中心

-   用户信息管理
-   BMI 计算和展示
-   目标设置
-   数据导出

## 🔧 开发说明

### 样式架构

-   使用 Styled-JSX 实现组件作用域样式
-   响应式断点：768px (mobile/desktop)
-   全局样式在 `App.css` 中定义

### 状态管理

-   基于 React Hooks (useState)
-   本地状态管理，无外部状态库
-   简单的页面路由系统

### 类型安全

-   严格的 TypeScript 配置
-   完整的类型定义
-   编译时类型检查
