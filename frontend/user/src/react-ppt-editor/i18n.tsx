const translations: Record<string, string> = {
  "editor.defaultText": "双击编辑文字",
  "editor.tableHeader": "表头",
  "editor.slide": "幻灯片",
  "editor.newTextBox": "新建文本框",
  "editor.newShape": "新建形状",
  "editor.insertPicture": "插入图片",
  "editor.insertTable": "插入表格",
  "editor.shortcutSlide": "右键空白区域可新增元素",
  "editor.fill": "填充色",
  "editor.stroke": "边框色",
  "editor.borderWidth": "边框宽度",
  "editor.picture": "图片",
  "editor.table": "表格",
  "editor.font": "字体",
  "editor.fontSize": "字号",
  "editor.color": "文字颜色",
  "editor.bold": "加粗",
  "editor.italic": "斜体",
  "editor.alignLeft": "左对齐",
  "editor.alignCenter": "居中",
  "editor.alignRight": "右对齐",
  "editor.text": "文字",
  "editor.shape": "形状",
  "editor.editText": "编辑文字",
  "editor.replacePicture": "替换图片",
  "editor.insertRow": "插入行",
  "editor.insertColumn": "插入列",
  "editor.duplicate": "复制",
  "editor.bringForward": "上移一层",
  "editor.sendBackward": "下移一层",
  "editor.delete": "删除",
  "editor.shortcutObject": "拖拽移动，拉伸控制点调整大小"
};

export function useLocale() {
  return {
    t: (key: string) => translations[key] ?? key
  };
}
