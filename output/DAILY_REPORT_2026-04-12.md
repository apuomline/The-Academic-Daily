# 学术日报 - 2026-04-12

> 本日报由 Academic Paper Pusher 自动生成
> 搜索关键词: llm
> 生成时间: 2026-04-12 18:54:03
> 数据源: arxiv

---


## 一、arXiv 预印本


### Ads in AI Chatbots? An Analysis of How Large Language Models Navigate Conflicts of Interest

**日期与版本**：2026-04-09 v1
**作者**：Addison J. Wu, Ryan Liu, Shuyue Stella Li, Yulia Tsvetkov, Thomas L. Griffiths
**分类**：cs.AI, cs.CL, cs.CY


【摘要翻译】
本文分析了大型语言模型在处理利益冲突时的行为。研究探讨了人工智能聊天机器人中广告投放的潜在问题，并分析了大型语言模型如何在这些冲突中做出决策。研究通过构建一个分析框架，对大型语言模型在广告投放中的行为进行了深入分析。

【创新点概述】
提出了一种名为“利益冲突导航分析框架”的方法，用于解决大型语言模型在处理广告投放时可能遇到的利益冲突问题。该框架首先构建了一个名为“冲突检测模块”，用于识别和分类聊天机器人中可能出现的利益冲突。接着，设计了“决策策略模块”，在冲突检测的基础上，为大型语言模型提供决策支持。在跨域和少样本的场景中进行了验证，结果表明该方法能够有效地帮助大型语言模型在广告投放中做出合理的决策。


**arXiv ID**：2604.08525v1
**PDF**：[下载](https://arxiv.org/pdf/2604.08525v1.pdf)

---


### What Drives Representation Steering? A Mechanistic Case Study on Steering Refusal

**日期与版本**：2026-04-09 v1
**作者**：Stephen Cheng, Sarah Wiegreffe, Dinesh Manocha
**分类**：cs.LG, cs.AI, cs.CL


【摘要翻译】
本文通过一项机制性案例研究，探讨了导致拒绝引导的原因。研究聚焦于拒绝引导的拒绝行为，分析了拒绝引导的动机、机制和影响因素。研究发现，拒绝引导的拒绝行为受到多种因素的影响，包括个体特征、情境因素和引导策略等。

【创新点概述】
提出“拒绝引导拒绝行为机制研究”框架，用于解决拒绝引导过程中拒绝行为产生的原因和影响因素。设计“动机分析模块”，在个体特征和情境因素层面分析了拒绝引导的动机；设计“机制分析模块”，在行为机制层面分析了拒绝引导的拒绝行为产生的原因；设计“影响因素分析模块”，在引导策略层面分析了拒绝引导的拒绝行为的影响因素。在拒绝引导的案例研究中验证，取得了对拒绝引导拒绝行为机制深入理解的效果。


**arXiv ID**：2604.08524v1
**PDF**：[下载](https://arxiv.org/pdf/2604.08524v1.pdf)

---


### Cram Less to Fit More: Training Data Pruning Improves Memorization of Facts

**日期与版本**：2026-04-09 v1
**作者**：Jiayuan Ye, Vitaly Feldman, Kunal Talwar
**分类**：cs.CL, stat.ML


【摘要翻译】
我们提出了一种基于训练损失的数据选择方案，旨在限制训练数据中的事实数量并平摊它们的频率分布。在包含高熵事实的半合成数据集上，我们的选择方法有效地将事实准确率提升至容量极限。当从头开始在标注的维基百科语料库上预训练语言模型时，我们的选择方法使得GPT2-Small模型（110m参数）能够记住比标准训练多1.3倍的事实实体，其性能与在完整数据集上预训练的10倍更大的模型（1.3B参数）相当。

【创新点概述】
提出了一种名为“Cram Less to Fit More”的框架，旨在解决训练数据中事实过多且分布不均的问题。该框架设计了一个基于训练损失的数据选择模块，通过限制训练数据中的事实数量并平摊它们的频率分布，有效地提升了事实的准确率。在半合成数据集上，该模块将事实准确率提升至容量极限。此外，当在标注的维基百科语料库上从头预训练语言模型时，该模块使得GPT2-Small模型能够记住比标准训练多1.3倍的事实实体，其性能与在完整数据集上预训练的10倍更大的模型相当。


**arXiv ID**：2604.08519v1
**PDF**：[下载](https://arxiv.org/pdf/2604.08519v1.pdf)

---


### What do Language Models Learn and When? The Implicit Curriculum Hypothesis

**日期与版本**：2026-04-09 v1
**作者**：Emmy Liu, Kaiser Sun, Millicent Li, Isabelle Lee, Lindia Tjuatja, Jen-tse Huang, Graham Neubig
**分类**：cs.CL


【摘要翻译】
本文探讨了语言模型在学习和何时学习的过程中所习得的内容。提出了隐含课程假设，该假设认为语言模型通过观察和模仿人类语言使用的方式，从大量的文本数据中学习语言结构和知识。研究通过分析语言模型在处理不同类型任务时的表现，揭示了模型学习的关键特征和潜在的学习路径。

【创新点概述】
提出隐含课程假设，用于解决语言模型学习过程中的关键问题。设计了一个名为“Language Model Learning Dynamics”（语言模型学习动态）的框架，用于分析语言模型在学习和何时学习的过程中所习得的内容。该框架提出了“Curriculum Learning Module”（课程学习模块），在数据流层面实现了对大量文本数据的观察和模仿。通过在“Language Model Performance Analysis”（语言模型性能分析）层面进行操作，揭示了模型学习的关键特征和潜在的学习路径。在跨域和少样本场景中验证了该框架，取得了对语言模型学习动态的深入理解。


**arXiv ID**：2604.08510v1
**PDF**：[下载](https://arxiv.org/pdf/2604.08510v1.pdf)

---


### sciwrite-lint: Verification Infrastructure for the Age of Science Vibe-Writing

**日期与版本**：2026-04-09 v1
**作者**：Sergey V Samsonau
**分类**：cs.DL, cs.CL, cs.SE


【摘要翻译】
我们提出了一种第三种选择：测量论文本身。sciwrite-lint（pip install sciwrite-lint）是一个开源的用于科学论文的代码检查工具，它完全在研究人员的机器上运行（免费公共数据库、单个消费级GPU和开放权重模型），无需将任何论文发送到外部服务。该管道验证参考文献是否存在，检查撤稿状态，将元数据与规范记录进行比较，下载并解析引用的论文，验证它们是否支持对其所做的声明，并进一步检查引用论文自身的参考文献。每个参考文献都获得一个按参考文献的可靠性得分，该得分汇总了所有验证信号。我们在arXiv和bioRxiv上对30篇未见过的论文进行了评估，包括错误注入和LLM裁决的假阳性分析。

作为一个实验性的扩展，我们提出了SciLint Score，它将完整性验证与贡献组件相结合，将科学哲学中的五个框架（Popper、Lakatos、Kitcher、Laudan、Mayo）转化为科学论证的可计算结构属性。完整性组件是工具的核心，并在本文中进行了评估；贡献组件作为实验代码发布，以供社区开发。

【创新点概述】
提出sciwrite-lint框架，用于解决科学论文写作中的验证问题。设计sciwrite-lint模块，实现从参考文献存在性验证到论文引用完整性的全面检查。该模块在研究人员的本地机器上运行，无需发送论文到外部服务，提高了数据安全和隐私保护。在arXiv和bioRxiv的30篇未见过的论文上进行了实验验证，通过错误注入和LLM裁决的假阳性分析，验证了该工具的有效性。此外，作为实验性扩展，提出了SciLint Score，将完整性验证与科学哲学框架相结合，通过将哲学框架转化为可计算的结构属性，为科学论证的评估提供了新的视角。


**arXiv ID**：2604.08501v1
**PDF**：[下载](https://arxiv.org/pdf/2604.08501v1.pdf)

---








## 统计信息

| 数据源 | 论文数量 |
|--------|----------|

| arxiv | 5 |

| **总计** | **5** |

---

*本日报由 [Academic Paper Pusher](https://github.com/your-repo) 自动生成*