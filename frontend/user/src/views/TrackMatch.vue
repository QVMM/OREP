<template>
  <main class="track-match-page">
    <section class="library-hero" aria-label="全赛道信息库说明">
      <div class="hero-copy">
        <span class="eyebrow">TRACK LIBRARY</span>
        <h1>赛道匹配</h1>
        <p>
          这里不是只给一个智能推荐结果，而是把世界职业院校技能大赛 42 个赛道完整列出来，帮助团队先理解所有赛道，再结合项目情况判断更适合的参赛方向。
        </p>
      </div>
      <div class="hero-stats">
        <article>
          <strong>42</strong>
          <span>完整赛道</span>
        </article>
        <article>
          <strong>12</strong>
          <span>赛道领域</span>
        </article>
        <article>
          <strong>AI</strong>
          <span>辅助匹配</span>
        </article>
      </div>
    </section>

    <section class="assistant-strip" aria-label="智能匹配辅助区">
      <div class="assistant-copy">
        <span>智能建议辅助</span>
        <h2>先看全赛道，再用项目画像做参考判断</h2>
        <p>智能匹配只作为辅助，不替代团队对全部赛道的理解。下方所有赛道都可作为备选方向进行比较。</p>
      </div>
      <div class="assistant-controls">
        <label>
          <span>项目方向</span>
          <select v-model="form.industry">
            <option v-for="option in industries" :key="option" :value="option">{{ option }}</option>
          </select>
        </label>
        <label>
          <span>核心技能</span>
          <select v-model="form.skill">
            <option v-for="option in skills" :key="option" :value="option">{{ option }}</option>
          </select>
        </label>
        <button type="button" @click="matched = true">生成参考建议</button>
      </div>
      <aside class="assistant-result" :class="{ 'is-active': matched }">
        <b>{{ matched ? '91' : '--' }}</b>
        <div>
          <strong>{{ matched ? '参考方向：现代农业 / 新一代信息技术' : '等待生成参考建议' }}</strong>
          <small>{{ matched ? '请继续查看 42 个赛道卡片，确认项目证据最能支撑哪个赛道。' : '选择项目方向和核心技能后生成辅助建议。' }}</small>
        </div>
      </aside>
    </section>

    <section class="track-library" aria-label="42个赛道详细信息">
      <header class="section-head">
        <div>
          <span class="eyebrow">ALL TRACKS</span>
          <h2>42 个赛道详细信息</h2>
          <p>每张卡片以项目资料卡方式呈现，重点说明赛道覆盖范围、适合项目、关键能力与需要准备的证明材料。</p>
        </div>
        <div class="library-filter" aria-label="赛道分类筛选">
          <button
            v-for="category in categories"
            :key="category"
            type="button"
            :class="{ active: selectedCategory === category }"
            @click="selectedCategory = category"
          >
            {{ category }}
          </button>
        </div>
      </header>

      <div class="track-grid">
        <article v-for="track in filteredTracks" :key="track.no" class="track-card" :class="`tone-${track.tone}`">
          <div class="track-art" aria-hidden="true">
            <div class="art-layer art-layer--back"></div>
            <div class="art-layer art-layer--mid"></div>
            <div class="art-layer art-layer--front"></div>
            <div class="art-title-band">
              <strong>{{ track.name }}</strong>
              <span>{{ String(track.no).padStart(2, '0') }} / {{ track.category }}</span>
            </div>
            <div class="art-meta">
              <span>{{ track.tags[0] }}</span>
              <span>{{ track.tags[1] }}</span>
              <span>{{ track.tags[2] }}</span>
            </div>
          </div>

          <div class="track-info">
            <div class="info-block">
              <h3>简介 <em>About</em></h3>
              <p>{{ track.scope }}</p>
            </div>

            <div class="info-block info-block--compact">
              <h4>适合项目 <em>Fit</em></h4>
              <p>{{ track.fit }}</p>
            </div>

            <div class="info-block info-block--compact">
              <h4>关键能力 <em>Ability</em></h4>
              <p>{{ track.ability }}</p>
            </div>

            <div class="info-block info-block--compact">
              <h4>材料建议 <em>Evidence</em></h4>
              <p>{{ track.evidence }}</p>
            </div>

            <button type="button">查看详情</button>
          </div>
        </article>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'

const matched = ref(false)
const selectedCategory = ref('全部')

const industries = ['现代农业', '智能制造', '信息技术', '交通运输', '医药健康', '文化服务']
const skills = ['物联网与数据采集', '机械设计与制造', '软件开发与算法', '运营服务与管理', '视觉表达与传播']

const form = reactive({
  industry: '现代农业',
  skill: '物联网与数据采集',
})

const tracks = [
  { no: 1, name: '现代农业赛道', category: '农林牧渔', scope: '覆盖种植、设施农业、农机应用、农产品生产与乡村产业服务。', fit: '适合围绕智慧农业、农产品提质、种植管理、农机服务展开的项目。', ability: '农业生产流程、设备使用、数据监测、现场管理与应用成效说明。', evidence: '准备种植数据、设备运行记录、试点照片、作物表现和用户反馈。', tags: ['农业', '设施', '数据'], tone: 'green' },
  { no: 2, name: '林业赛道', category: '农林牧渔', scope: '覆盖林业培育、森林资源保护、生态修复、园林绿化与林产品服务。', fit: '适合森林管护、绿化养护、生态监测、林业资源数字化项目。', ability: '资源识别、管护流程、生态指标、作业规范和风险控制。', evidence: '准备巡检记录、地图标注、生态指标、作业流程和前后对比材料。', tags: ['林业', '生态', '管护'], tone: 'green' },
  { no: 3, name: '畜牧与水产赛道', category: '农林牧渔', scope: '覆盖养殖管理、动物健康、水产生产、饲养环境控制与质量安全。', fit: '适合智慧养殖、疫病预警、饲喂管理、水质监测等项目。', ability: '养殖流程、环境参数、健康监测、质量控制和安全规范。', evidence: '准备养殖数据、水质记录、设备照片、健康指标和经济效益说明。', tags: ['养殖', '水产', '监测'], tone: 'green' },
  { no: 4, name: '资源开采赛道', category: '资源环境', scope: '覆盖矿产资源、采掘作业、安全生产、资源利用与智能化管理。', fit: '适合资源勘查、开采安全、设备监测、绿色矿山相关项目。', ability: '工艺流程、安全风险、设备运维、资源效率和合规意识。', evidence: '准备作业流程、安全方案、监测数据、设备记录和风险闭环材料。', tags: ['资源', '安全', '设备'], tone: 'slate' },
  { no: 5, name: '地质勘察与地理测绘赛道', category: '资源环境', scope: '覆盖工程测量、地理信息、遥感应用、地质调查与空间数据处理。', fit: '适合测绘建模、空间分析、灾害监测、地理信息应用项目。', ability: '测量精度、数据处理、地图表达、模型应用和现场作业规范。', evidence: '准备测绘成果、精度报告、地图图层、现场照片和数据处理流程。', tags: ['测绘', 'GIS', '空间'], tone: 'slate' },
  { no: 6, name: '生态保护与环境治理赛道', category: '资源环境', scope: '覆盖污染治理、生态修复、环境监测、低碳减排与资源循环。', fit: '适合环保监测、废弃物处理、节能减排、生态治理项目。', ability: '环境指标、治理工艺、监测方法、效果评估和持续运营。', evidence: '准备检测数据、治理前后对比、工艺图、现场记录和合规材料。', tags: ['环保', '低碳', '治理'], tone: 'green' },
  { no: 7, name: '能源动力赛道', category: '能源材料', scope: '覆盖电力、热能、新能源、能源设备运行维护与节能管理。', fit: '适合新能源应用、能源监测、设备节能、用能优化项目。', ability: '能源系统理解、设备运行、效率分析、安全规范和维护能力。', evidence: '准备能耗数据、设备参数、运行日志、节能测算和安全方案。', tags: ['能源', '新能源', '节能'], tone: 'orange' },
  { no: 8, name: '材料赛道', category: '能源材料', scope: '覆盖材料制备、检测、成型加工、性能评价与应用转化。', fit: '适合新材料应用、材料检测、工艺优化、产品性能提升项目。', ability: '材料性能、工艺参数、检测方法、质量控制和应用验证。', evidence: '准备检测报告、样品照片、性能数据、工艺流程和应用场景证明。', tags: ['材料', '检测', '工艺'], tone: 'orange' },
  { no: 9, name: '土木建筑设计与管理赛道', category: '土木建筑', scope: '覆盖建筑设计、BIM、工程造价、项目管理、绿色建筑与运维。', fit: '适合 BIM 应用、绿色建筑、工程管理、造价优化和运维管理项目。', ability: '设计表达、模型构建、成本进度、规范校核和项目管理。', evidence: '准备 BIM 模型、图纸、算量表、进度计划、能耗测算和管理记录。', tags: ['BIM', '设计', '管理'], tone: 'blue' },
  { no: 10, name: '土木建筑施工赛道', category: '土木建筑', scope: '覆盖建筑施工、装配式施工、测量放线、质量安全和施工组织。', fit: '适合施工工艺优化、智慧工地、安全管理、质量追溯项目。', ability: '施工流程、现场操作、质量验收、安全控制和组织协同。', evidence: '准备施工流程、现场照片、质量记录、安全交底和验收材料。', tags: ['施工', '质量', '安全'], tone: 'blue' },
  { no: 11, name: '水利赛道', category: '土木建筑', scope: '覆盖水利工程、灌溉排水、水环境治理、防汛监测与运维管理。', fit: '适合水利监测、灌溉控制、防汛预警、水资源管理项目。', ability: '水文数据、工程运维、风险预警、设备控制和服务场景理解。', evidence: '准备水位流量数据、设备运行记录、预警方案、现场图和应用效果。', tags: ['水利', '监测', '运维'], tone: 'blue' },
  { no: 12, name: '机械设计与制造赛道', category: '装备制造', scope: '覆盖机械设计、加工制造、数控工艺、质量检测与产品装配。', fit: '适合机械结构创新、加工工艺优化、检测夹具、装备改良项目。', ability: '机械设计、加工参数、装配调试、质量检测和工艺改进。', evidence: '准备图纸、三维模型、加工过程、检测报告、样机照片和测试数据。', tags: ['机械', '制造', '检测'], tone: 'slate' },
  { no: 13, name: '智能装备应用赛道', category: '装备制造', scope: '覆盖机器人、自动化产线、智能控制、设备联调与场景应用。', fit: '适合自动化改造、机器人应用、智能产线、设备控制项目。', ability: '设备集成、控制逻辑、联调能力、产线效率和安全运维。', evidence: '准备控制流程、联调视频、运行数据、节拍对比和安全方案。', tags: ['智能装备', '自动化', '机器人'], tone: 'slate' },
  { no: 14, name: '机电设备安装与运维赛道', category: '装备制造', scope: '覆盖机电安装、设备调试、故障诊断、维护保养与安全管理。', fit: '适合设备运维、故障诊断、智能巡检、安装调试优化项目。', ability: '安装规范、调试流程、故障排查、维护计划和安全意识。', evidence: '准备设备台账、故障案例、维修记录、巡检表和运行前后对比。', tags: ['机电', '运维', '诊断'], tone: 'slate' },
  { no: 15, name: '航空交通运输赛道', category: '交通运输', scope: '覆盖航空服务、机场运行、航空设备维护、安全保障与流程管理。', fit: '适合机场服务优化、航空保障、设备巡检、安全流程改进项目。', ability: '服务流程、安全规范、设备维护、应急处置和协同调度。', evidence: '准备服务流程图、演练记录、设备检查表、风险预案和评价反馈。', tags: ['航空', '服务', '安全'], tone: 'blue' },
  { no: 16, name: '轨道交通运输赛道', category: '交通运输', scope: '覆盖城市轨道、铁路运营、设备维护、客运服务与调度管理。', fit: '适合轨交服务、设备检测、运营调度、安全管理项目。', ability: '运营规则、设备维护、调度协同、服务改进和安全控制。', evidence: '准备运营流程、设备记录、调度方案、服务评价和应急演练。', tags: ['轨道', '运营', '调度'], tone: 'blue' },
  { no: 17, name: '道路与管道运输赛道', category: '交通运输', scope: '覆盖道路运输、车辆调度、管道运输、物流安全与运维管理。', fit: '适合运输调度、车辆管理、道路安全、管网监测项目。', ability: '运输组织、路线优化、设备监测、安全管理和成本控制。', evidence: '准备路线数据、调度记录、监测图表、安全方案和效率对比。', tags: ['道路', '管道', '调度'], tone: 'blue' },
  { no: 18, name: '船舶交通运输赛道', category: '交通运输', scope: '覆盖船舶运行、港口服务、航运管理、船舶设备维护与安全。', fit: '适合港口服务、船舶维护、航运调度、水上安全项目。', ability: '航运流程、设备检查、安全规范、服务协同和风险处置。', evidence: '准备港航流程、设备记录、安全演练、服务反馈和运行数据。', tags: ['船舶', '港口', '航运'], tone: 'blue' },
  { no: 19, name: '新一代信息技术赛道', category: '信息技术', scope: '覆盖软件开发、云计算、大数据、物联网、网络安全和系统集成。', fit: '适合平台系统、数据应用、物联网控制、网络安全、数字化工具项目。', ability: '需求分析、系统架构、数据处理、功能实现、安全与部署能力。', evidence: '准备系统截图、代码说明、接口文档、测试数据、部署记录和用户反馈。', tags: ['软件', '数据', '物联网'], tone: 'blue' },
  { no: 20, name: '人工智能赛道', category: '信息技术', scope: '覆盖机器学习、智能识别、智能决策、生成式 AI 与行业应用。', fit: '适合 AI 识别、预测、推荐、智能问答、自动化决策项目。', ability: '数据集构建、模型训练、效果评估、应用落地和伦理安全。', evidence: '准备样本数据、模型指标、对比实验、使用场景和风险控制说明。', tags: ['AI', '模型', '算法'], tone: 'blue' },
  { no: 21, name: '电子电器与集成电路赛道', category: '电子电气', scope: '覆盖电子产品设计制造、电器装调、集成电路、检测维修与质量控制。', fit: '适合电子硬件、智能终端、电路检测、电器维修、芯片应用项目。', ability: '电路设计、装调检测、故障排查、质量控制和安全规范。', evidence: '准备原理图、PCB、测试报告、装调过程、故障案例和产品照片。', tags: ['电子', '电器', '检测'], tone: 'orange' },
  { no: 22, name: '轻工赛道', category: '轻纺食品', scope: '覆盖轻工产品设计、生产工艺、质量检测、包装与绿色制造。', fit: '适合日用品改良、工艺优化、包装设计、质量提升项目。', ability: '产品工艺、材料选择、检测评价、用户体验和绿色生产。', evidence: '准备样品照片、工艺流程、检测数据、用户反馈和成本分析。', tags: ['轻工', '产品', '质量'], tone: 'orange' },
  { no: 23, name: '纺织服装赛道', category: '轻纺食品', scope: '覆盖服装设计、面料工艺、智能制造、品牌展示与质量管理。', fit: '适合服装设计、面料创新、智能制衣、品牌展示项目。', ability: '设计表达、制版工艺、面料应用、质量控制和市场定位。', evidence: '准备设计稿、样衣照片、工艺说明、面料检测和展示视频。', tags: ['纺织', '服装', '设计'], tone: 'orange' },
  { no: 24, name: '食品与粮食赛道', category: '轻纺食品', scope: '覆盖食品加工、粮食储运、质量检测、营养健康与食品安全。', fit: '适合食品工艺、检测溯源、保鲜储运、健康食品项目。', ability: '食品安全、加工流程、检测方法、质量控制和标准意识。', evidence: '准备检测报告、工艺流程、样品照片、溯源记录和用户反馈。', tags: ['食品', '检测', '安全'], tone: 'orange' },
  { no: 25, name: '医药生产与经营赛道', category: '医药健康', scope: '覆盖药品生产、质量管理、药品经营、用药服务与合规运营。', fit: '适合药品管理、质量追溯、药事服务、经营流程优化项目。', ability: '药品规范、质量控制、流通管理、服务流程和合规意识。', evidence: '准备流程图、质控记录、追溯材料、服务案例和合规说明。', tags: ['医药', '质量', '合规'], tone: 'green' },
  { no: 26, name: '医疗器械制造与运维赛道', category: '医药健康', scope: '覆盖医疗器械制造、检测、安装调试、维修维护与安全管理。', fit: '适合医疗设备维护、检测工具、器械改良、运维管理项目。', ability: '设备原理、检测调试、维修流程、质量安全和使用规范。', evidence: '准备设备记录、检测报告、维修案例、调试视频和安全风险说明。', tags: ['医疗器械', '运维', '检测'], tone: 'green' },
  { no: 27, name: '医学技术赛道', category: '医药健康', scope: '覆盖医学检验、影像技术、康复评估、健康检测与技术服务。', fit: '适合医学检测、影像辅助、健康评估、技术服务流程优化项目。', ability: '检测流程、数据解读、服务规范、质量控制和伦理边界。', evidence: '准备检测流程、样本记录、质量控制表、案例说明和隐私保护方案。', tags: ['医学', '检测', '服务'], tone: 'green' },
  { no: 28, name: '康复治疗与护理赛道', category: '医药健康', scope: '覆盖康复训练、护理服务、健康照护、评估干预与人文关怀。', fit: '适合康复设备、护理流程、健康管理、照护服务项目。', ability: '评估干预、护理规范、服务沟通、风险控制和效果跟踪。', evidence: '准备评估表、训练记录、服务流程、效果对比和用户反馈。', tags: ['康复', '护理', '照护'], tone: 'green' },
  { no: 29, name: '财经赛道', category: '财经商贸', scope: '覆盖会计、金融、税务、数据分析、财务管理与经营决策。', fit: '适合财务数字化、成本分析、经营看板、金融服务项目。', ability: '数据核算、风险控制、经营分析、合规意识和决策支持。', evidence: '准备财务模型、数据报表、分析过程、合规说明和决策案例。', tags: ['财经', '数据', '经营'], tone: 'blue' },
  { no: 30, name: '商贸赛道', category: '财经商贸', scope: '覆盖市场营销、电商运营、客户服务、品牌推广与商业模式。', fit: '适合电商运营、品牌营销、门店服务、用户增长项目。', ability: '市场分析、运营策划、客户服务、数据复盘和商业表达。', evidence: '准备运营数据、营销素材、客户反馈、销售记录和复盘报告。', tags: ['商贸', '电商', '营销'], tone: 'blue' },
  { no: 31, name: '物流与供应链赛道', category: '财经商贸', scope: '覆盖仓储配送、供应链计划、物流信息化、运输组织与成本优化。', fit: '适合仓储优化、配送调度、供应链可视化、物流降本项目。', ability: '流程设计、库存管理、路径优化、信息系统和成本控制。', evidence: '准备流程图、库存数据、配送记录、效率对比和成本测算。', tags: ['物流', '供应链', '仓储'], tone: 'blue' },
  { no: 32, name: '旅游赛道', category: '文旅服务', scope: '覆盖旅游服务、景区运营、导游讲解、文旅产品设计与数字文旅。', fit: '适合文旅路线、景区服务、研学旅行、数字导览项目。', ability: '服务设计、讲解表达、用户体验、运营管理和文化传播。', evidence: '准备路线方案、讲解视频、用户评价、运营数据和文旅素材。', tags: ['旅游', '文旅', '服务'], tone: 'orange' },
  { no: 33, name: '餐饮赛道', category: '文旅服务', scope: '覆盖烹饪制作、餐饮服务、营养搭配、食品安全与门店运营。', fit: '适合菜品创新、餐饮服务、营养餐、门店流程优化项目。', ability: '制作工艺、服务流程、食品安全、成本控制和体验设计。', evidence: '准备菜品照片、制作流程、成本表、卫生记录和顾客反馈。', tags: ['餐饮', '服务', '安全'], tone: 'orange' },
  { no: 34, name: '艺术设计赛道', category: '文化艺术', scope: '覆盖视觉传达、产品设计、环境艺术、数字媒体与品牌设计。', fit: '适合品牌视觉、产品包装、空间设计、数字媒体设计项目。', ability: '审美表达、设计逻辑、用户研究、作品落地和传播效果。', evidence: '准备设计稿、成品照片、用户调研、迭代过程和应用场景。', tags: ['设计', '视觉', '品牌'], tone: 'purple' },
  { no: 35, name: '表演艺术赛道', category: '文化艺术', scope: '覆盖音乐、舞蹈、戏剧、舞台呈现、活动编排与艺术传播。', fit: '适合舞台作品、表演编排、艺术活动、文化传播项目。', ability: '艺术表现、节目组织、舞台调度、观众体验和文化阐释。', evidence: '准备排练记录、演出视频、编排说明、观众反馈和传播数据。', tags: ['表演', '舞台', '传播'], tone: 'purple' },
  { no: 36, name: '新闻传播赛道', category: '文化艺术', scope: '覆盖新闻采编、短视频制作、新媒体运营、内容传播与舆情分析。', fit: '适合融媒体作品、短视频传播、校园媒体、品牌内容项目。', ability: '选题策划、内容生产、传播运营、数据复盘和伦理规范。', evidence: '准备作品链接、传播数据、脚本分镜、运营记录和版权说明。', tags: ['传播', '媒体', '内容'], tone: 'purple' },
  { no: 37, name: '教育与体育赛道', category: '公共服务', scope: '覆盖教学设计、课程实施、体育训练、活动组织和学习评价。', fit: '适合智慧教育、课程资源、体育训练、学习评价项目。', ability: '教学设计、活动组织、评价反馈、安全管理和育人价值。', evidence: '准备课程设计、课堂记录、训练数据、评价表和学生反馈。', tags: ['教育', '体育', '评价'], tone: 'green' },
  { no: 38, name: '公共安全、管理与服务赛道', category: '公共服务', scope: '覆盖公共服务、应急管理、社区治理、安全防范与服务优化。', fit: '适合社区服务、应急预案、公共安全、治理数字化项目。', ability: '服务流程、风险识别、组织协同、应急处置和管理闭环。', evidence: '准备服务台账、应急演练、风险清单、用户反馈和治理成效。', tags: ['公共服务', '安全', '治理'], tone: 'slate' },
  { no: 39, name: '健康养老与婴幼儿托育赛道', category: '公共服务', scope: '覆盖养老服务、婴幼儿托育、健康管理、照护支持与服务运营。', fit: '适合养老照护、托育服务、健康监测、家庭支持项目。', ability: '照护规范、服务沟通、安全风险、健康评估和运营管理。', evidence: '准备服务流程、评估记录、照护案例、家属反馈和安全方案。', tags: ['养老', '托育', '健康'], tone: 'green' },
  { no: 40, name: '生物技术赛道', category: '医药健康', scope: '覆盖生物实验、检测分析、发酵工程、生命科学应用与质量控制。', fit: '适合生物检测、实验流程优化、发酵应用、科普转化项目。', ability: '实验规范、数据分析、质量控制、安全伦理和应用验证。', evidence: '准备实验记录、检测数据、样品照片、对照结果和安全说明。', tags: ['生物', '实验', '检测'], tone: 'green' },
  { no: 41, name: '化工技术赛道', category: '能源材料', scope: '覆盖化工生产、工艺控制、质量检测、安全环保与产品应用。', fit: '适合化工工艺优化、检测控制、安全环保、材料制备项目。', ability: '工艺参数、质量检测、安全控制、环保意识和应用说明。', evidence: '准备工艺流程、检测报告、参数记录、安全方案和环保材料。', tags: ['化工', '工艺', '安全'], tone: 'orange' },
  { no: 42, name: '汽车制造与维修赛道', category: '装备制造', scope: '覆盖汽车制造、检测维修、新能源汽车、智能网联与服务管理。', fit: '适合新能源汽车维护、车辆检测、智能网联、服务流程项目。', ability: '车辆结构、检测诊断、维修流程、安全规范和客户服务。', evidence: '准备故障案例、检测数据、维修记录、设备照片和服务反馈。', tags: ['汽车', '新能源', '维修'], tone: 'slate' },
]

const categories = computed(() => ['全部', ...new Set(tracks.map((track) => track.category))])

const filteredTracks = computed(() => {
  if (selectedCategory.value === '全部') return tracks
  return tracks.filter((track) => track.category === selectedCategory.value)
})
</script>

<style scoped>
.track-match-page {
  min-height: 100vh;
  padding: 92px clamp(18px, 4vw, 56px) 88px;
  background-color: #ffffff;
  background-image: none;
  color: #182739;
}

.library-hero,
.assistant-strip,
.track-library {
  width: min(1280px, 100%);
  margin: 0 auto;
}

.library-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 430px);
  gap: 24px;
  align-items: stretch;
}

.hero-copy,
.hero-stats,
.assistant-strip,
.track-library,
.track-card {
  border: 1px solid rgba(31, 52, 80, 0.1);
  background: rgba(255, 255, 255, 0.86);
}

.hero-copy {
  padding: clamp(30px, 5vw, 54px);
}

.eyebrow {
  color: #0d61c8;
  font-size: 12px;
  font-weight: 950;
  letter-spacing: 0.16em;
}

.hero-copy h1 {
  margin: 12px 0 18px;
  font-size: clamp(42px, 6vw, 78px);
  line-height: 0.96;
  letter-spacing: -0.06em;
}

.hero-copy p,
.assistant-copy p,
.section-head p {
  margin: 0;
  color: #67798b;
  font-size: 17px;
  line-height: 1.85;
  font-weight: 650;
}

.hero-stats {
  padding: 24px;
  display: grid;
  gap: 12px;
  background:
    linear-gradient(135deg, rgba(6, 45, 100, 0.94), rgba(10, 97, 190, 0.9)),
    linear-gradient(90deg, rgba(255, 255, 255, 0.12) 1px, transparent 1px),
    linear-gradient(rgba(255, 255, 255, 0.12) 1px, transparent 1px);
  background-size: auto, 18px 18px, 18px 18px;
  color: #fff;
}

.hero-stats article {
  padding: 18px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  background: rgba(255, 255, 255, 0.08);
}

.hero-stats strong {
  display: block;
  font-size: 42px;
  line-height: 1;
}

.hero-stats span {
  display: block;
  margin-top: 8px;
  color: rgba(255, 255, 255, 0.72);
  font-size: 14px;
  font-weight: 800;
}

.assistant-strip {
  margin-top: 22px;
  padding: 24px;
  display: grid;
  grid-template-columns: 1fr minmax(360px, 520px) minmax(280px, 340px);
  gap: 22px;
  align-items: center;
}

.assistant-copy span {
  color: #f06d22;
  font-size: 13px;
  font-weight: 950;
}

.assistant-copy h2,
.section-head h2 {
  margin: 8px 0 10px;
  font-size: clamp(24px, 3vw, 36px);
  letter-spacing: -0.04em;
}

.assistant-controls {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 12px;
}

.assistant-controls label {
  display: grid;
  gap: 8px;
}

.assistant-controls label span {
  color: #25384d;
  font-size: 13px;
  font-weight: 900;
}

.assistant-controls select,
.assistant-controls button {
  height: 46px;
  border: 1px solid #d7e0ea;
  background: #fff;
  color: #24384d;
  font: inherit;
}

.assistant-controls select {
  padding: 0 12px;
}

.assistant-controls button {
  align-self: end;
  padding: 0 18px;
  border-color: #14263a;
  background: #14263a;
  color: #fff;
  font-weight: 900;
  cursor: pointer;
}

.assistant-result {
  min-height: 114px;
  padding: 18px;
  display: flex;
  gap: 16px;
  align-items: center;
  border: 1px solid rgba(13, 97, 200, 0.14);
  background: #f7fbff;
}

.assistant-result b {
  width: 78px;
  height: 78px;
  display: grid;
  place-items: center;
  border: 8px solid #dce8f6;
  border-radius: 50%;
  color: #0d61c8;
  font-size: 28px;
}

.assistant-result.is-active b {
  border-color: #0d61c8;
}

.assistant-result strong {
  display: block;
  color: #1f3145;
  font-size: 16px;
  line-height: 1.4;
}

.assistant-result small {
  display: block;
  margin-top: 6px;
  color: #718294;
  line-height: 1.55;
}

.track-library {
  margin-top: 22px;
  padding: 28px;
}

.section-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 520px);
  gap: 22px;
  align-items: start;
}

.library-filter {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.library-filter button {
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid #d7e0ea;
  background: #fff;
  color: #5f7184;
  font-size: 13px;
  font-weight: 850;
  cursor: pointer;
}

.library-filter button.active {
  border-color: #14263a;
  background: #14263a;
  color: #fff;
}

.track-grid {
  margin-top: 32px;
  display: grid;
  grid-template-columns: 1fr;
  gap: 42px;
}

.track-card {
  position: relative;
  display: grid;
  grid-template-columns: minmax(320px, 430px) minmax(0, 1fr);
  gap: clamp(38px, 6vw, 74px);
  align-items: center;
  padding: 0;
  border: 0;
  background: transparent;
}

.tone-green { --tone: #1d8d65; }
.tone-blue { --tone: #0d61c8; }
.tone-orange { --tone: #f07a2a; }
.tone-slate { --tone: #536173; }
.tone-purple { --tone: #7352c7; }

.tone-green { --tone-soft: #ecf8f3; }
.tone-blue { --tone-soft: #edf4ff; }
.tone-orange { --tone-soft: #fff2e8; }
.tone-slate { --tone-soft: #f0f3f6; }
.tone-purple { --tone-soft: #f3efff; }

.track-art {
  position: relative;
  min-height: 520px;
  overflow: hidden;
  background: color-mix(in srgb, var(--tone, #0d61c8) 22%, #f0f1fb);
  box-shadow: 0 28px 72px rgba(30, 45, 80, 0.12);
}

.art-layer {
  position: absolute;
  background: color-mix(in srgb, var(--tone, #0d61c8) 28%, #f4f4fb);
  opacity: 0.7;
}

.art-layer--back {
  inset: 28px 118px 150px 20px;
  transform: skewY(8deg);
}

.art-layer--mid {
  inset: 62px 100px 170px 54px;
  background: color-mix(in srgb, var(--tone, #0d61c8) 38%, #e9ebfb);
}

.art-layer--front {
  left: 86px;
  right: -26px;
  bottom: 98px;
  height: 58%;
  border-radius: 0 0 46% 0;
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.42), color-mix(in srgb, var(--tone, #0d61c8) 35%, #ffffff));
}

.art-layer--front::before,
.art-layer--front::after {
  content: "";
  position: absolute;
  inset: 22px 28px auto auto;
  width: 78%;
  height: 72%;
  border-radius: 0 0 44% 0;
  border: 18px solid rgba(255, 255, 255, 0.22);
  border-top: 0;
  border-left: 0;
}

.art-layer--front::after {
  inset: 52px 56px auto auto;
  width: 62%;
  height: 58%;
}

.art-title-band {
  position: absolute;
  left: 58px;
  right: 0;
  top: 118px;
  min-height: 128px;
  padding: 24px 28px;
  display: grid;
  align-content: center;
  gap: 10px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.88), rgba(255, 255, 255, 0.68));
}

.art-title-band strong {
  color: #1d1d24;
  font-size: clamp(28px, 3vw, 42px);
  line-height: 1.18;
  letter-spacing: 0.08em;
  font-weight: 950;
}

.art-title-band span {
  width: max-content;
  padding: 8px 12px;
  background: color-mix(in srgb, var(--tone, #0d61c8) 82%, #fff);
  color: #fff;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.08em;
}

.art-meta {
  position: absolute;
  left: 34px;
  right: 34px;
  bottom: 30px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.art-meta span {
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.72);
  color: color-mix(in srgb, var(--tone, #0d61c8) 72%, #172334);
  font-size: 12px;
  font-weight: 900;
}

.track-info {
  padding: 18px 0;
}

.info-block + .info-block {
  margin-top: 28px;
}

.info-block h3,
.info-block h4 {
  margin: 0 0 14px;
  color: #223242;
  font-size: 28px;
  line-height: 1.2;
  font-weight: 900;
}

.info-block h4 {
  font-size: 22px;
}

.info-block em {
  margin-left: 8px;
  color: #273443;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 19px;
  font-weight: 400;
}

.info-block p {
  margin: 0;
  max-width: 720px;
  color: #8293a5;
  font-size: 22px;
  line-height: 1.78;
  font-weight: 700;
}

.info-block--compact p {
  font-size: 18px;
  line-height: 1.7;
}

.track-info button {
  margin-top: 34px;
  min-width: 164px;
  height: 58px;
  border: 1px solid #cfd7df;
  border-radius: 6px;
  background: #fff;
  color: #263748;
  font-size: 22px;
  font-weight: 850;
  cursor: pointer;
}

@media (max-width: 1180px) {
  .library-hero,
  .assistant-strip,
  .section-head {
    grid-template-columns: 1fr;
  }

  .assistant-controls {
    grid-template-columns: 1fr 1fr;
  }

  .assistant-controls button {
    grid-column: 1 / -1;
  }

  .library-filter {
    justify-content: flex-start;
  }

  .track-card {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .track-match-page {
    padding: 78px 14px 116px;
  }

  .hero-copy,
  .hero-stats,
  .assistant-strip,
  .track-library,
  .track-card {
    padding: 20px;
  }

  .assistant-controls,
  .track-grid {
    grid-template-columns: 1fr;
  }

  .track-art {
    min-height: 380px;
  }

  .art-title-band {
    left: 30px;
    top: 92px;
  }

  .info-block p {
    font-size: 18px;
  }

  .info-block--compact p {
    font-size: 16px;
  }
}
</style>
