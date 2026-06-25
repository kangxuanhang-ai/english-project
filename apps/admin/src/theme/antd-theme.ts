import type { ThemeConfig } from 'antd'

export const adminTheme: ThemeConfig = {
  token: {
    colorPrimary: '#4338ca',
    colorLink: '#4338ca',
    colorBgLayout: '#faf9f6',
    colorBgContainer: '#ffffff',
    colorText: '#18181b',
    colorTextSecondary: '#71717a',
    colorBorder: '#e4e4e7',
    borderRadius: 12,
    borderRadiusLG: 16,
    fontFamily: "'Plus Jakarta Sans', 'PingFang SC', 'Microsoft YaHei', sans-serif",
    controlHeight: 36,
    controlHeightLG: 40,
  },
  components: {
    Layout: {
      siderBg: '#ffffff',
      headerBg: '#ffffff',
      bodyBg: '#faf9f6',
    },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: '#eef2ff',
      itemSelectedColor: '#4338ca',
      itemHoverBg: '#f4f4f5',
      itemBorderRadius: 10,
      iconSize: 16,
    },
    Card: { paddingLG: 20 },
    Table: {
      headerBg: '#fafafa',
      headerColor: '#71717a',
      rowHoverBg: '#faf9ff',
    },
    Button: {
      primaryShadow: '0 2px 0 rgba(67,56,202,0.08)',
    },
  },
}
