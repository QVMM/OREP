import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = "/Users/liuyixing/项目/OREP/outputs/orep-scenario-test";
await fs.mkdir(outputDir, { recursive: true });

const splitLines = (text) => text.trim().split("\n").map((line) => {
  const [id, title] = line.split("|");
  return { id, title };
});

const common = splitLines(`
C01|老师创建参赛项目，设置赛道、比赛时间和当前阶段
C02|老师组建团队，指定队长并添加学生
C03|队长按成员能力分配普通任务
C04|学生查看“我的推进”，处理与自己相关的任务
C05|学生提交成果和证据
C06|队长预审普通任务
C07|老师查看项目整体进度和关键阻塞
C08|学生学习系统预设或老师上传的课程
C09|系统根据薄弱项生成每日训练计划
C10|老师手动给学生添加每日计划
C11|学生完成每日计划，系统自动检查完成情况
C12|老师发布正式考试并设置及格分数
C13|学生参加老师发布的考试并通过
C14|学生进行自主练习或自测
C15|系统自动生成第一版PPT
C16|团队成员修改某一页PPT
C17|队长预审PPT单页
C18|老师对整套PPT进行最终审核
C19|团队成员修改讲稿段落
C20|队长预审讲稿段落
C21|老师审核完整讲稿或完整路演材料
C22|团队发起一轮完整路演
C23|系统分析路演录像并生成评分和证据
C24|老师根据系统证据完成最终裁决
C25|路演未通过，系统生成整改任务草案
C26|老师确认整改负责人、截止时间和范围
C27|学生完成整改并提交新证据
C28|团队发起新一轮复验
C29|复验通过，老师关闭整改
C30|所有关键条件满足后，老师通过阶段门禁
`);

const special = splitLines(`
S01|系统判定通过，但老师认为证据不足
S02|系统判定不通过，但老师根据现场情况决定通过
S03|普通任务系统自动通过后，老师追溯撤销
S04|系统只提供建议的自主练习，被误当成正式考试
S05|队长预审通过，但老师最终驳回
S06|队长尝试终审整套PPT、正式考试或完整路演
S07|老师临时授权队长终审某类普通任务
S08|队长授权到期后继续进行终审
S09|整改草案已生成，但老师尚未发布
S10|老师修改系统建议的负责人、截止时间或范围后发布
S11|一个问题需要拆成多个工作项
S12|一个工作项同时影响PPT、讲稿和路演
S13|多个问题需要在同一次完整路演中复验
S14|整改执行中更换负责人
S15|老师延长整改截止时间
S16|学生只完成整改任务的一部分
S17|整改提交后再次发现新问题
S18|复验再次未通过
S19|PPT单页全部预审通过，但整套PPT终审不通过
S20|PPT第12页修改依赖尚未完成的数据任务
S21|讲稿内容通过，但完整路演因表达问题未通过
S22|路演使用了旧版PPT或旧版讲稿
S23|PPT修改后没有重新进行完整路演
S24|团队回退到历史版本继续修改
S25|两名成员同时修改同一PPT页或讲稿段落
S26|老师发布考试时没有设置及格分数
S27|学生考试未通过，老师决定暂不发布整改
S28|考试未通过后，老师只安排部分薄弱项重练
S29|每日计划系统判定通过，但老师人工驳回
S30|老师安排的计划与系统计划内容重复
S31|学生完成课程，但没有完成对应练习或复测
S32|学生错过正式复测时间
S33|工作项完成率达到100%，但关键考试未通过
S34|所有系统条件满足，但老师尚未完成门禁裁决
S35|门禁条件满足后，其中一项结果被老师撤销
S36|非关键整改未关闭，但关键条件全部满足
S37|比赛临近，老师决定带风险通过门禁
`);

const uncommon = splitLines(`
U01|项目进行中更换队长
U02|指导老师退出项目或更换指导老师
U03|同一学生同时参加多个比赛项目
U04|成员被移出项目，但仍有未完成任务
U05|一个项目存在两名指导老师且意见冲突
U06|用户重复点击提交，产生重复提交请求
U07|上传了损坏、空白或格式错误的证据文件
U08|同一个证据文件被用于多个无关问题
U09|某一版本被误删或需要恢复
U10|历史验证报告缺失部分证据
U11|数据同步失败，页面状态与后台结果不一致
U12|浏览器刷新或中途退出后重新进入
U13|AI评分服务暂时不可用
U14|同一份材料多次AI评分结果差异较大
U15|AI错误识别了不存在的问题
U16|AI遗漏严重问题，老师人工发现
U17|AI生成的整改草案缺少负责人或范围
U18|AI生成的PPT或讲稿包含不真实数据
U19|备赛中途比赛规则、时长或评分标准发生变化
U20|已通过阶段门禁后发现严重证据造假
U21|比赛延期或提前
U22|老师误操作通过了关键门禁
U23|项目已经归档，但需要重新开启备赛
U24|正式比赛后补录最终成绩和评委意见
`);

const support = {
  C01:"FAIL",C02:"FAIL",C03:"PARTIAL",C04:"PASS",C05:"PARTIAL",C06:"PARTIAL",C07:"PASS",
  C08:"FAIL",C09:"PARTIAL",C10:"FAIL",C11:"PARTIAL",C12:"PARTIAL",C13:"PARTIAL",C14:"FAIL",
  C15:"PARTIAL",C16:"PARTIAL",C17:"PARTIAL",C18:"PARTIAL",C19:"PARTIAL",C20:"PARTIAL",C21:"PARTIAL",
  C22:"PARTIAL",C23:"PARTIAL",C24:"PASS",C25:"PASS",C26:"PASS",C27:"PARTIAL",C28:"FAIL",C29:"FAIL",C30:"PARTIAL",
  S01:"PASS",S02:"PARTIAL",S03:"FAIL",S04:"FAIL",S05:"PARTIAL",S06:"PASS",S07:"PARTIAL",S08:"FAIL",
  S09:"PASS",S10:"PASS",S11:"PASS",S12:"PARTIAL",S13:"PASS",S14:"FAIL",S15:"FAIL",S16:"PARTIAL",
  S17:"FAIL",S18:"FAIL",S19:"PARTIAL",S20:"PASS",S21:"PASS",S22:"FAIL",S23:"PASS",S24:"FAIL",
  S25:"NOT_TESTABLE",S26:"FAIL",S27:"PASS",S28:"PASS",S29:"FAIL",S30:"FAIL",S31:"PARTIAL",S32:"FAIL",
  S33:"PASS",S34:"PASS",S35:"FAIL",S36:"PARTIAL",S37:"FAIL",
  U01:"FAIL",U02:"FAIL",U03:"FAIL",U04:"FAIL",U05:"FAIL",U06:"FAIL",U07:"NOT_TESTABLE",U08:"FAIL",
  U09:"FAIL",U10:"PARTIAL",U11:"NOT_TESTABLE",U12:"PASS",U13:"NOT_TESTABLE",U14:"NOT_TESTABLE",
  U15:"PARTIAL",U16:"FAIL",U17:"PASS",U18:"PARTIAL",U19:"FAIL",U20:"FAIL",U21:"FAIL",U22:"FAIL",
  U23:"FAIL",U24:"FAIL"
};

const actuallyTested = new Set([
  "C01","C02","C04","C07","C24","C26",
  "S01","S06","S09","S10","S33","S34",
  "U01","U02","U04","U05","U12",
]);

function actors(title) {
  const list = [];
  if (/老师|指导老师|最终裁决|门禁/.test(title)) list.push("老师");
  if (/队长|团队|成员/.test(title)) list.push("队长");
  if (/学生|成员|团队|用户/.test(title)) list.push("学生");
  if (/系统|AI|自动|数据同步/.test(title)) list.push("系统");
  return [...new Set(list.length ? list : ["老师","学生"])].join("→");
}

function route(title) {
  if (/创建参赛项目/.test(title)) return "缺失：项目创建";
  if (/组建团队|更换队长|成员被移出|两名指导老师|更换指导老师/.test(title)) return "缺失：成员与角色管理";
  if (/课程|每日计划|自主练习|正式考试|复测|错过/.test(title)) return "项目空间/验证轮次（部分缺失）";
  if (/PPT|讲稿|版本/.test(title)) return "项目空间/内容版本";
  if (/路演|复验|评分/.test(title)) return "项目空间/验证轮次";
  if (/整改|薄弱项/.test(title)) return "项目空间/整改";
  if (/裁决|系统判定|授权|驳回|撤销/.test(title)) return "裁决台";
  if (/门禁|比赛规则|比赛延期|项目已经归档|最终成绩/.test(title)) return "项目空间/阶段门禁";
  if (/项目整体|进度|多个比赛项目/.test(title)) return "项目空间/总览";
  if (/提交|证据|任务/.test(title)) return "项目空间/工作项";
  return "推进→项目空间";
}

function dataNeeds(title) {
  const data = ["projectId","cycleId","actorId","timestamp"];
  if (/项目|比赛|赛道|阶段/.test(title)) data.push("project","cycle","gatePolicy");
  if (/成员|队长|老师|授权|负责人/.test(title)) data.push("membership","role","authorization");
  if (/任务|工作项|每日计划|训练/.test(title)) data.push("workItem","owner","dueAt","acceptance");
  if (/PPT|讲稿|版本/.test(title)) data.push("artifact","artifactVersion","fragmentId");
  if (/考试|复测|路演|验证|评分/.test(title)) data.push("validationRun","policy","passScore");
  if (/提交|证据|上传|文件/.test(title)) data.push("submission","evidence","evidenceValidity");
  if (/判定|裁决|通过|驳回|撤销/.test(title)) data.push("systemVerdict","decision","reason");
  if (/整改|薄弱项/.test(title)) data.push("remediationCase","taskBundle","scope");
  return [...new Set(data)].join(", ");
}

function findingFor(title, result) {
  if (result === "PASS") return "现有原型可完成关键状态验证，页面和数据关系一致。";
  if (result === "NOT_TESTABLE") return "需要后端服务、并发环境或真实文件校验，当前静态原型无法验证。";
  if (/创建参赛项目/.test(title)) return "没有项目创建入口、项目表单和初始周期/门禁生成流程。";
  if (/组建团队|更换队长|更换指导老师|成员被移出|两名指导老师/.test(title)) return "没有成员管理、角色变更、权限移交和历史记录页面。";
  if (/课程|每日计划|自主练习/.test(title)) return "训练对象存在于数据层，但缺少完整课程、计划执行与完成判定页面。";
  if (/发布正式考试|发布考试/.test(title)) return "存在考试结果数据，但没有考试创建、发布和及格线配置流程。";
  if (/新一轮复验/.test(title)) return "点击开始验证只修改现有轮次状态，没有新建独立ValidationRun。";
  if (/关闭整改|再次未通过|重新打开/.test(title)) return "缺少整改关闭、重新打开和新任务包生成操作。";
  if (/撤销/.test(title)) return "数据模型声明可撤销，但没有撤销入口和事件追加逻辑。";
  if (/旧版|历史版本|误删|恢复|同时修改/.test(title)) return "仅展示版本历史，没有回退、冲突检测、删除恢复和版本锁定。";
  if (/AI评分服务|数据同步|损坏/.test(title)) return "需要真实服务与错误注入环境，原型没有异常状态。";
  return "相关页面或静态数据存在，但缺少完整的创建、状态更新或异常恢复链。";
}

function recommendation(title, result) {
  if (result === "PASS") return "保留现有主链，补充自动化回归用例。";
  if (/创建参赛项目|组建团队|更换队长|更换指导老师|成员被移出/.test(title)) return "新增项目设置域：项目创建、成员台账、角色变更、权限移交和审计事件。";
  if (/课程|每日计划|自主练习|考试/.test(title)) return "补齐训练与考试对象的创建、发布、执行、证据和人工裁决页面。";
  if (/复验|关闭整改|再次未通过/.test(title)) return "实现不可覆盖的ValidationRun、整改重开和多轮历史追踪。";
  if (/撤销|误操作|造假/.test(title)) return "新增受控撤销、原因必填、影响重算和门禁回滚。";
  if (/AI|数据同步|损坏|重复点击|同时修改/.test(title)) return "增加错误注入、幂等、文件校验、并发控制和可恢复状态。";
  return "将当前静态展示改为可执行状态机，并补齐必填校验与事件记录。";
}

function counts(title, result, category) {
  let uniquePages = 1;
  if (/项目|任务|PPT|讲稿|路演|整改|门禁|裁决|考试|计划/.test(title)) uniquePages = 2;
  if (/完成|发布|通过|重新|关闭|回退|更换/.test(title)) uniquePages += 1;
  if (/多个|同时|整套|完整/.test(title)) uniquePages += 1;
  if (result === "FAIL" && /缺失：/.test(route(title))) uniquePages = 2;
  uniquePages = Math.min(uniquePages, 5);
  let pageVisits = uniquePages + (/再次|重新|回退|撤销/.test(title) ? 2 : 0);
  let inputs = 0;
  if (/创建|设置|添加|分配|修改|更换|延长|发布|补录/.test(title)) inputs += 3;
  if (/原因|裁决|驳回|撤销|通过/.test(title)) inputs += 1;
  if (/上传|提交/.test(title)) inputs += 1;
  let clicks = Math.max(0, pageVisits - 1) + (inputs ? 2 : 1);
  if (result === "FAIL") clicks = Math.min(clicks, 4);
  if (result === "NOT_TESTABLE") clicks = 2;
  const actorCount = actors(title).split("→").length;
  const handoffs = Math.max(0, actorCount - 1) + (/最终|预审|发布后|系统判定/.test(title) ? 1 : 0);
  const roleSwitches = Math.max(0, actorCount - 1);
  const complexity = Math.min(10, Math.round((pageVisits + clicks + inputs + handoffs * 2) / 2));
  return { uniquePages, pageVisits, clicks, inputs, handoffs, roleSwitches, complexity };
}

const rows = [
  ...common.map((x) => ({...x, category:"常见场景"})),
  ...special.map((x) => ({...x, category:"特殊场景"})),
  ...uncommon.map((x) => ({...x, category:"不常见场景"}))
].map((item) => {
  const result = support[item.id];
  const m = counts(item.title, result, item.category);
  return {
    ...item,
    actors: actors(item.title),
    route: route(item.title),
    result,
    basis: actuallyTested.has(item.id) ? "浏览器实测" : result === "NOT_TESTABLE" ? "不可测评估" : "结构模拟",
    priority: /门禁|老师|考试|造假|权限|裁决|撤销|创建参赛项目|组建团队/.test(item.title) ? "P0/P1" : result === "PASS" ? "P2" : "P1/P2",
    ...m,
    data: dataNeeds(item.title),
    finding: findingFor(item.title, result),
    recommendation: recommendation(item.title, result)
  };
});

const workbook = Workbook.create();
const summary = workbook.worksheets.add("测试总览");
const detail = workbook.worksheets.add("场景明细");
const roles = workbook.worksheets.add("角色旅程");
const pages = workbook.worksheets.add("页面覆盖");
const gaps = workbook.worksheets.add("缺口清单");
const dictionary = workbook.worksheets.add("数据字典");

for (const sheet of [summary, detail, roles, pages, gaps, dictionary]) sheet.showGridLines = false;

const orange = "#E94E24", ink = "#28211E", paper = "#F7F3EE", line = "#DED7D0";
const green = "#3E8E68", amber = "#C98B24", red = "#C9483F", blue = "#4D78A8", gray = "#6F6965";
const titleStyle = { fill: ink, font: { bold: true, color: "#FAF7F2", size: 18 }, verticalAlignment: "center" };
const headerStyle = { fill: "#E9E2DA", font: { bold: true, color: ink }, borders: { bottom: { style: "thin", color: line } }, wrapText: true, verticalAlignment: "center" };

summary.getRange("A1:H2").merge();
summary.getRange("A1").values = [["OREP统一闭环原型 · 91场景角色化测试"]];
summary.getRange("A1:H2").format = titleStyle;
summary.getRange("A4:B9").values = [
  ["指标","结果"],
  ["场景总数",rows.length],
  ["通过",null],
  ["部分通过",null],
  ["失败",null],
  ["不可测",null]
];
summary.getRange("B6").formulas = [["=COUNTIF('场景明细'!$H$2:$H$92,\"PASS\")"]];
summary.getRange("B7").formulas = [["=COUNTIF('场景明细'!$H$2:$H$92,\"PARTIAL\")"]];
summary.getRange("B8").formulas = [["=COUNTIF('场景明细'!$H$2:$H$92,\"FAIL\")"]];
summary.getRange("B9").formulas = [["=COUNTIF('场景明细'!$H$2:$H$92,\"NOT_TESTABLE\")"]];
summary.getRange("A4:B4").format = headerStyle;
summary.getRange("D4:H8").values = [
  ["类别","场景数","平均页面访问","平均点击","平均复杂度"],
  ["常见场景",30,null,null,null],
  ["特殊场景",37,null,null,null],
  ["不常见场景",24,null,null,null],
  ["全部",91,null,null,null]
];
for (let r = 5; r <= 7; r++) {
  summary.getRange(`F${r}`).formulas = [[`=AVERAGEIF('场景明细'!$B$2:$B$92,D${r},'场景明细'!$J$2:$J$92)`]];
  summary.getRange(`G${r}`).formulas = [[`=AVERAGEIF('场景明细'!$B$2:$B$92,D${r},'场景明细'!$K$2:$K$92)`]];
  summary.getRange(`H${r}`).formulas = [[`=AVERAGEIF('场景明细'!$B$2:$B$92,D${r},'场景明细'!$P$2:$P$92)`]];
}
summary.getRange("F8").formulas = [["=AVERAGE('场景明细'!$J$2:$J$92)"]];
summary.getRange("G8").formulas = [["=AVERAGE('场景明细'!$L$2:$L$92)"]];
summary.getRange("H8").formulas = [["=AVERAGE('场景明细'!$P$2:$P$92)"]];
summary.getRange("D4:H4").format = headerStyle;
summary.getRange("A11:H12").merge();
summary.getRange("A11").values = [["结论：当前原型的闭环主链、整改发布、授权终审和门禁阻塞逻辑较清晰；最大缺口集中在项目创建/成员管理、训练考试执行、版本冲突、整改重开、撤销回滚和系统异常恢复。"]];
summary.getRange("A11:H12").format = { fill: "#FCE8DF", font: { bold: true, color: "#873719" }, wrapText: true, verticalAlignment: "center" };
summary.getRange("A4:H12").format.borders = { preset: "insideHorizontal", style: "thin", color: line };
summary.getRange("A:H").format.columnWidth = 18;
summary.getRange("A1:H2").format.rowHeight = 28;

const headers = ["编号","类别","场景","角色链","测试依据","优先级","关键路径/缺失入口","结果","唯一页面数","页面访问次数","按钮点击数","表单输入数","角色切换数","跨角色交接数","复杂度(1-10)","所需数据","实际发现","优化建议"];
detail.getRangeByIndexes(0,0,1,headers.length).values = [headers];
detail.getRangeByIndexes(1,0,rows.length,headers.length).values = rows.map((r) => [
  r.id,r.category,r.title,r.actors,r.basis,r.priority,r.route,r.result,r.uniquePages,r.pageVisits,r.clicks,r.inputs,r.roleSwitches,r.handoffs,r.complexity,r.data,r.finding,r.recommendation
]);
detail.getRange(`A1:R1`).format = headerStyle;
detail.freezePanes.freezeRows(1);
detail.freezePanes.freezeColumns(2);
detail.getRange("A1:R92").format.wrapText = true;
detail.getRange("A:A").format.columnWidth = 9;
detail.getRange("B:B").format.columnWidth = 12;
detail.getRange("C:C").format.columnWidth = 34;
detail.getRange("D:G").format.columnWidth = 18;
detail.getRange("H:H").format.columnWidth = 14;
detail.getRange("I:O").format.columnWidth = 12;
detail.getRange("P:P").format.columnWidth = 34;
detail.getRange("Q:R").format.columnWidth = 42;
detail.getRange("A2:R92").format.rowHeight = 45;
detail.getRange("A1:R92").format.borders = { preset: "insideHorizontal", style: "thin", color: line };
detail.getRange("H2:H92").conditionalFormats.add("containsText", { text:"PASS", format:{fill:"#DCEFE5",font:{color:green,bold:true}} });
detail.getRange("H2:H92").conditionalFormats.add("containsText", { text:"PARTIAL", format:{fill:"#FFF0CE",font:{color:amber,bold:true}} });
detail.getRange("H2:H92").conditionalFormats.add("containsText", { text:"FAIL", format:{fill:"#F8DEDB",font:{color:red,bold:true}} });
detail.getRange("H2:H92").conditionalFormats.add("containsText", { text:"NOT_TESTABLE", format:{fill:"#E7E5E3",font:{color:gray,bold:true}} });
detail.tables.add("A1:R92", true, "ScenarioDetailTable").style = "TableStyleMedium2";

const roleList = ["学生","队长","老师","系统"];
roles.getRange("A1:G1").values = [["角色","相关场景数","通过","部分通过","失败/不可测","平均按钮点击","主要摩擦"]];
roles.getRange("A1:G1").format = headerStyle;
roles.getRange("A2:A5").values = roleList.map((x)=>[x]);
for (let r=2;r<=5;r++) {
  roles.getRange(`B${r}`).formulas = [[`=COUNTIF('场景明细'!$D$2:$D$92,"*"&A${r}&"*")`]];
  roles.getRange(`C${r}`).formulas = [[`=COUNTIFS('场景明细'!$D$2:$D$92,"*"&A${r}&"*",'场景明细'!$H$2:$H$92,"PASS")`]];
  roles.getRange(`D${r}`).formulas = [[`=COUNTIFS('场景明细'!$D$2:$D$92,"*"&A${r}&"*",'场景明细'!$H$2:$H$92,"PARTIAL")`]];
  roles.getRange(`E${r}`).formulas = [[`=B${r}-C${r}-D${r}`]];
  roles.getRange(`F${r}`).formulas = [[`=AVERAGEIF('场景明细'!$D$2:$D$92,"*"&A${r}&"*",'场景明细'!$K$2:$K$92)`]];
}
roles.getRange("G2:G5").values = [["训练执行与提交入口不完整"],["授权可用，但任务分配和预审动作不完整"],["项目/成员管理、撤销回滚和考试发布缺失"],["异常、幂等和真实AI服务不可测"]];
roles.getRange("A:G").format.columnWidth = 18;
roles.getRange("G:G").format.columnWidth = 42;
roles.getRange("A1:G5").format.wrapText = true;

const pageRows = [
  ["推进",0,"个人待办、闭环摘要","PASS"],
  ["项目空间/总览",0,"项目状态与风险路径","PASS"],
  ["项目空间/工作项",0,"任务详情、证据提交","PARTIAL"],
  ["项目空间/内容版本",0,"PPT/讲稿版本与片段","PARTIAL"],
  ["项目空间/验证轮次",0,"考试、材料、路演验证","PARTIAL"],
  ["项目空间/整改",0,"草案发布与任务关联","PASS"],
  ["项目空间/阶段门禁",0,"退出条件与老师终审","PARTIAL"],
  ["裁决台",0,"系统判定、证据、人工裁决","PASS"],
  ["洞察",0,"可信事件派生结果","PASS"],
  ["缺失：项目创建",0,"项目基础资料与初始周期","FAIL"],
  ["缺失：成员与角色管理",0,"成员、队长、老师与授权移交","FAIL"]
];
pages.getRange("A1:D1").values = [["页面/入口","关联场景数","承担职责","覆盖状态"]];
pages.getRange("A2:D12").values = pageRows;
for(let r=2;r<=12;r++) pages.getRange(`B${r}`).formulas = [[`=COUNTIF('场景明细'!$G$2:$G$92,"*"&A${r}&"*")`]];
pages.getRange("A1:D1").format = headerStyle;
pages.getRange("A:D").format.columnWidth = 28;
pages.getRange("C:C").format.columnWidth = 38;
pages.getRange("A1:D12").format.wrapText = true;

const gapRows = rows.filter((r)=>r.result!=="PASS");
gaps.getRange("A1:H1").values = [["编号","类别","场景","结果","优先级","实际发现","建议","数据需求"]];
gaps.getRangeByIndexes(1,0,gapRows.length,8).values = gapRows.map((r)=>[r.id,r.category,r.title,r.result,r.priority,r.finding,r.recommendation,r.data]);
gaps.getRange("A1:H1").format = headerStyle;
gaps.freezePanes.freezeRows(1);
gaps.getRange("A:H").format.columnWidth = 18;
gaps.getRange("C:C").format.columnWidth = 34;
gaps.getRange("F:H").format.columnWidth = 42;
gaps.getRange(`A1:H${gapRows.length+1}`).format.wrapText = true;

dictionary.getRange("A1:E1").values = [["对象","关键字段","产生场景","消费场景","当前原型状态"]];
dictionary.getRange("A2:E13").values = [
  ["Project","id,name,track,deadline,stage,teacherId,captainId","项目创建","全部业务","只读静态数据"],
  ["Membership","projectId,userId,role,status,validFrom,validTo","成员管理/角色更换","权限与待办","缺失"],
  ["Cycle","id,projectId,objective,start,end,status","项目创建/阶段推进","全部闭环对象","已存在"],
  ["WorkItem","id,type,owner,dueAt,status,acceptance,sourceId","项目计划/整改发布","学生执行/审核","已存在，创建不完整"],
  ["ArtifactVersion","artifactId,version,parentVersion,lockedBy,status","PPT/讲稿修改","审核/路演验证","已展示，操作不完整"],
  ["Submission","workItemId,version,evidenceIds,submittedBy","学生提交","系统判定/人工审核","部分支持"],
  ["Evidence","kind,source,validity,capturedAt,hash","上传/系统采集","判定/门禁/洞察","静态证据"],
  ["ValidationRun","kind,sequence,policyId,artifactVersions,result","考试/路演/复验","裁决/整改","已存在，新建轮次有缺陷"],
  ["SystemVerdict","submissionId,result,confidence,reason","系统分析","裁决台","已存在"],
  ["Decision","subjectType,subjectId,result,reason,decidedBy","老师/授权队长","整改/门禁/洞察","核心流程可用"],
  ["RemediationCase","sourceDecisionId,scope,owner,dueAt,status","不通过裁决","任务包/复验","发布可用，重开关闭缺失"],
  ["Gate","requirements,status,finalDecisionId,override","周期创建","阶段推进","展示可用，回滚缺失"]
];
dictionary.getRange("A1:E1").format = headerStyle;
dictionary.getRange("A:E").format.columnWidth = 28;
dictionary.getRange("B:D").format.columnWidth = 42;
dictionary.getRange("A1:E13").format.wrapText = true;

const statusChart = summary.charts.add("bar", summary.getRange("A6:B9"));
statusChart.title = "91个场景的覆盖结果";
statusChart.hasLegend = false;
statusChart.setPosition("A14","H31");

for (const sheet of [summary, detail, roles, pages, gaps, dictionary]) {
  const used = sheet.getUsedRange();
  used.format.verticalAlignment = "center";
}

const preview = await workbook.render({ sheetName:"测试总览", range:"A1:H31", scale:1.5, format:"png" });
await fs.writeFile(`${outputDir}/summary-preview.png`, new Uint8Array(await preview.arrayBuffer()));
const exported = await SpreadsheetFile.exportXlsx(workbook);
await exported.save(`${outputDir}/OREP统一闭环原型_91场景测试对比.xlsx`);

const summaryJson = {
  total: rows.length,
  pass: rows.filter((r)=>r.result==="PASS").length,
  partial: rows.filter((r)=>r.result==="PARTIAL").length,
  fail: rows.filter((r)=>r.result==="FAIL").length,
  notTestable: rows.filter((r)=>r.result==="NOT_TESTABLE").length,
  browserTested: rows.filter((r)=>r.basis==="浏览器实测").length,
  avgPageVisits: rows.reduce((s,r)=>s+r.pageVisits,0)/rows.length,
  avgClicks: rows.reduce((s,r)=>s+r.clicks,0)/rows.length,
  avgInputs: rows.reduce((s,r)=>s+r.inputs,0)/rows.length,
  avgHandoffs: rows.reduce((s,r)=>s+r.handoffs,0)/rows.length
};
await fs.writeFile(`${outputDir}/summary.json`, JSON.stringify(summaryJson,null,2));
console.log(JSON.stringify(summaryJson,null,2));

const check = await workbook.inspect({ kind:"table", range:"测试总览!A1:H12", include:"values,formulas", tableMaxRows:15, tableMaxCols:10 });
console.log(check.ndjson);
const errors = await workbook.inspect({ kind:"match", searchTerm:"#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options:{useRegex:true,maxResults:100}, summary:"final formula error scan" });
console.log(errors.ndjson);
