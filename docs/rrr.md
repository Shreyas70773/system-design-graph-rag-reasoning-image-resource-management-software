# Research Paper Reviews

## Using the DOM Tree for Content Extraction

**Authors:** Sergio López, Josep Silva, David Insa

**Abstract:**
This paper addresses the challenge of isolating the main textual content of a webpage from surrounding elements such as menus and advertisements. The authors propose a DOM-based approach that exploits the hierarchical structure of webpages to identify cohesive content blocks without relying on templates or language-dependent features.

**Methodology:**
The approach computes a characters-to-nodes ratio (CNR) for each DOM node and propagates high-CNR nodes bottom-up to identify candidate content blocks. The block with the highest relevant text density is selected as the main content.

**Findings:**
Our investigation reveals high recall and competitive precision across diverse webpages. We observe improved robustness compared to tag-ratio methods, although precision can drop when non-content sections contain dense text.

---

## Scalable Deep Learning Logo Detection

**Authors:** Hang Su, Shaogang Gong, Xiatian Zhu

**Abstract:**
This paper addresses the scalability limitations of traditional logo detection systems, which rely on small datasets and exhaustive bounding box annotations. The authors propose a webly supervised learning framework that leverages noisy, weakly labeled web data to enable large-scale logo detection across many brand classes.

**Methodology:**
The authors introduce Scalable Logo Self-co-Learning (SL²), which combines synthetic data bootstrapping with incremental self-learning and cross-model co-learning using Faster R-CNN and YOLOv2. Training data is progressively refined from noisy web images collected at scale.

**Findings:**
Our investigation reveals substantial performance gains over both strongly and weakly supervised baselines, achieving a mean average precision of 46.9%. We observe that incremental co-learning and context-aware data augmentation effectively mitigate noise and class imbalance, though scalability depends on careful confidence thresholding.

---

## In-Depth Benchmarking of Graph Database Systems with the LDBC Social Network Benchmark

**Authors:** Florin Rusu, Zhiyi Huang

**Abstract:**
This paper presents a comprehensive performance evaluation of native graph database systems using the LDBC Social Network Benchmark. The study compares Neo4j and TigerGraph across interactive and business intelligence workloads at multiple scale factors, aiming to understand scalability and efficiency trade-offs in large-scale graph processing.

**Methodology:**
The authors implement all 46 LDBC SNB queries in Cypher and GSQL and evaluate execution time, loading cost, and storage size across scale factors from 1 GB to 1 TB on multiple hardware configurations. Median runtimes are reported to ensure stability.

**Findings:**
Our investigation reveals that TigerGraph consistently outperforms Neo4j on complex and large-scale workloads, especially at higher scale factors. We observe that while Neo4j loads data faster initially, its indexing overhead limits scalability for large graph workloads.

---

## Explaining Dimensionality Reduction Results Using Shapley Values

**Authors:** Wilson E. Marcílio-Jr, Danilo M. Eler

**Abstract:**
This paper focuses on improving the interpretability of dimensionality reduction (DR) techniques by explaining how individual features contribute to the formation of clusters in low-dimensional projections. The authors propose a cluster-oriented explanation method that uses Shapley values to quantify feature contributions, enabling analysts to better understand non-linear DR outcomes.

**Methodology:**
The proposed method, ClusterShapley, applies KernelSHAP to estimate feature contributions after DR by mapping clusters in the projected space back to the high-dimensional data. Feature contributions are visualized using coordinated scatter plots, dot plots, and heatmaps.

**Findings:**
Our investigation reveals that Shapley-based explanations effectively capture feature influence on cluster formation across medical and social datasets. We observe improved interpretability of non-linear DR results, although computational cost increases with dataset size and dimensionality.

---

## No-Reference Image Quality Assessment via Transformers, Relative Ranking, and Self-Consistency

**Authors:** S. Alireza Golestaneh, Saba Dadsetan, Kris M. Kitani

**Abstract:**
This paper addresses the challenge of predicting perceptual image quality without access to a reference image. The authors propose a hybrid deep learning model that combines convolutional neural networks with Transformer-based self-attention to capture both local and non-local image features, aiming to improve robustness on authentically distorted images.

**Methodology:**
The proposed TReS model extracts multi-scale CNN features and applies Transformer encoders to model non-local dependencies. Training incorporates a relative ranking loss and a self-consistency loss based on equivariant image transformations such as horizontal flipping.

**Findings:**
Our investigation reveals state-of-the-art performance across multiple synthetic and real-world IQA datasets. We observe improved generalization and robustness to transformations, though training incurs higher computational cost due to additional ranking and consistency constraints.

---

## Equivalent Topologies on the Contracting Boundary

**Authors:** Vivian He

**Abstract:**
This paper investigates the relationship between two generalizations of the Gromov boundary for proper geodesic metric spaces: the contracting boundary and the κ-Morse boundary. The author proves that when the sublinear function κ is constant, these two boundaries are not only equivalent as sets but also share the same topology, resolving a previously conjectured relationship.

**Methodology:**
The study provides a theoretical comparison of boundary definitions by analyzing quasi-geodesic behavior and neighborhood systems. Formal proofs are constructed to show equivalence of open sets under both topologies using quasi-geodesic image theorems.

**Findings:**
Our investigation reveals that the 1-Morse boundary and the contracting boundary are topologically equivalent. We observe that this result guarantees metrizability of the contracting boundary for all proper geodesic metric spaces, strengthening earlier results limited to group settings.

---

## A Comprehensive Survey on Automatic Knowledge Extraction from Web Data

**Authors:** Al-Moslmi et al.

**Abstract:**
This paper provides a broad survey of techniques used for extracting structured knowledge from unstructured and semi-structured web data. It reviews the evolution of knowledge extraction methods from rule-based systems to modern deep learning approaches, highlighting their applicability across domains such as information retrieval, question answering, and knowledge graph construction.

**Methodology:**
The authors systematically categorize existing methods into rule-based, statistical, and neural approaches, comparing them across extraction tasks, data sources, and evaluation metrics. The survey also discusses common system architectures used in large-scale extraction pipelines.

**Findings:**
Our investigation reveals a clear trade-off between extraction accuracy and system generality. We observe that while neural methods improve adaptability, they often require substantial annotated data and introduce challenges related to explainability and error propagation.

---

## On Solutions of Certain Non-Linear Differential–Difference Equations

**Authors:** Garima Pant, Sanjay Kumar Pant

**Abstract:**
This paper studies the existence and structural form of transcendental entire solutions to specific classes of non-linear differential–difference equations involving shifts, derivatives, and exponential terms. Using tools from Nevanlinna theory, the authors analyze growth properties and derive conditions under which solutions must take restricted exponential forms.

**Methodology:**
The analysis applies Nevanlinna theory, logarithmic derivative lemmas, and growth estimates to transform the differential–difference equations into functional constraints. Case-based proofs are used to characterize admissible entire solutions under finite-order assumptions.

**Findings:**
Our investigation reveals that finite-order transcendental solutions are highly constrained and often reduce to simple exponential forms. We observe that imposing growth conditions eliminates broad classes of solutions, highlighting strong rigidity in such equations.

---

## Direct Preference Optimization: Your Language Model is Secretly a Reward Model

**Authors:** Rafael Rafailov, Archit Sharma, Eric Mitchell, Stefano Ermon, Christopher D. Manning, Chelsea Finn

**Abstract:**
This paper proposes Direct Preference Optimization (DPO), a method for aligning language models with human preferences without explicit reward modeling or reinforcement learning. The authors reformulate the RLHF objective to directly optimize a policy using preference data via a simple classification loss. The approach simplifies training while retaining alignment quality across tasks such as summarization, dialogue, and sentiment control.

**Methodology:**
The method derives a closed-form relationship between reward functions and optimal policies under KL constraints, replacing RL with a binary cross-entropy objective. Experiments compare DPO with PPO-based RLHF across controlled sentiment, summarization, and dialogue tasks.

**Findings:**
We observe that DPO matches or exceeds PPO-based RLHF while being more stable and computationally efficient. Our investigation reveals improved robustness to sampling temperature and competitive generalization under distribution shifts.

---

## Knowledge Graph Enhanced Large Language Model Editing

**Authors:** Mengqi Zhang, Xiaotian Ye, Qiang Liu, Pengjie Ren, Shu Wu, Zhumin Chen

**Abstract:**
This paper addresses the limitation of existing large language model (LLM) editing methods, which typically modify isolated facts without accounting for changes in associated knowledge. The authors propose a knowledge-graph-enhanced editing framework, GLAME, that captures and integrates related knowledge updates to improve post-edit generalization and multi-hop reasoning.

**Methodology:**
The method constructs an edit-induced subgraph from an external knowledge graph and encodes it using a relational graph neural network. The aggregated graph representation is then injected into a rank-one model editing framework to update specific LLM parameters in a single edit.

**Findings:**
Our investigation reveals that GLAME consistently outperforms state-of-the-art editing methods on COUNTERFACT, COUNTERFACTPLUS, and MQUAKE benchmarks. We observe notable gains in generalization and multi-hop reasoning, though performance depends on the availability and quality of external knowledge graphs.

---

## Graph Retrieval-Augmented Generation for Knowledge-Intensive Tasks

**Authors:** Yixin Cao, Hao Wang, Yiming Yang

**Abstract:**
This paper investigates retrieval-augmented generation using graph-structured knowledge to address limitations of text-only retrieval in knowledge-intensive generation tasks. The authors propose leveraging explicit graph neighborhoods to provide richer contextual grounding, enabling multi-hop reasoning and improved factual consistency in generated outputs.

**Methodology:**
The proposed framework constructs a knowledge graph from retrieved documents and performs neighborhood expansion to gather related entities and relations. This graph-augmented context is then serialized and fed into a large language model during generation.

**Findings:**
Our investigation reveals that graph-based retrieval improves performance on multi-hop QA and factual generation benchmarks. We observe reduced hallucinations compared to standard RAG, though the approach introduces additional preprocessing and retrieval overhead.

---

## AUTOSCRAPER: A Progressive Understanding Web Agent for Web Scraper Generation

**Authors:** Wenhao Huang, Zhouhong Gu, Chenghao Peng, Zhixu Li, Jiaqing Liang, Yanghua Xiao, Liqian Wen, Zulong Chen

**Abstract:**
This paper addresses the scalability limitations of wrapper-based and language-agent-based web scraping methods in dynamic web environments. The authors propose AUTOSCRAPER, a framework that combines LLM reasoning with reusable action sequences to generate executable web scrapers capable of generalizing across pages within the same website.

**Methodology:**
The framework uses a two-stage process: progressive generation, which incrementally constructs XPath action sequences using DOM hierarchy, and synthesis, which selects the most reusable sequence across multiple pages. A new executability metric is introduced for evaluation.

**Findings:**
Our investigation reveals that AUTOSCRAPER consistently outperforms wrapper-based and LLM-only baselines across multiple datasets and LLMs. We observe improved reusability and lower failure rates, although performance remains dependent on the LLM's ability to understand complex HTML structures.

---

## From Local to Global: A GraphRAG Approach to Query-Focused Summarization

**Authors:** Darren Edge, Ha Trinh, Newman Cheng, Joshua Bradley, Alex Chao, Apurva Mody, Steven Truitt, Dasha Metropolitansky, Robert Osazuwa Ness, Jonathan Larson

**Abstract:**
This paper addresses the limitations of conventional retrieval-augmented generation (RAG) systems in answering global, sensemaking queries over large document collections. The authors propose GraphRAG, a graph-based retrieval and summarization framework that enables query-focused summarization by leveraging entity relationships and hierarchical community structure within a corpus.

**Methodology:**
GraphRAG constructs an entity-centric knowledge graph from document chunks using LLM-based extraction, partitions the graph into hierarchical communities, and generates community summaries. Query answering is performed via a map-reduce process over these summaries to produce a global response.

**Findings:**
Our investigation reveals that GraphRAG consistently outperforms vector-based RAG on comprehensiveness and diversity for global queries across large corpora. We observe substantial gains in sensemaking capability with significantly lower token usage at higher community levels, though indexing introduces additional preprocessing cost.

---

## GRAG: Graph Retrieval-Augmented Generation

**Authors:** Yuntong Hu, Zhihan Lei, Zheng Zhang, Bo Pan, Chen Ling, Liang Zhao

**Abstract:**
This paper addresses the limitations of traditional retrieval-augmented generation (RAG) methods when applied to networked documents such as citation graphs, social media, and knowledge graphs. The authors propose Graph Retrieval-Augmented Generation (GRAG), a framework that retrieves query-relevant textual subgraphs and integrates both textual and topological information into large language models to support multi-hop reasoning.

**Methodology:**
GRAG employs a divide-and-conquer retrieval strategy that first selects relevant K-hop ego-graphs using semantic similarity, followed by soft pruning to remove irrelevant nodes and edges. Generation is guided using both hierarchical text descriptions (hard prompts) and graph-encoded representations (soft prompts).

**Findings:**
Our investigation reveals that GRAG consistently outperforms standard RAG and LLM baselines on multi-hop graph reasoning benchmarks. We observe improved factual grounding and reasoning depth, although retrieval quality depends on accurate node ranking and pruning.

---

## NoteLLM-2: Multimodal Large Representation Models for Recommendation

**Authors:** Chao Zhang, Haoxin Zhang, Shiwei Wu, Di Wu, Tong Xu, Xiangyu Zhao, Yan Gao, Yao Hu, Enhong Chen

**Abstract:**
This paper investigates the use of large language models to enhance multimodal representation learning for item-to-item recommendation tasks. The authors propose NoteLLM-2, a framework designed to mitigate the tendency of end-to-end fine-tuned multimodal models to underutilize visual information, thereby improving balanced multimodal understanding.

**Methodology:**
The approach integrates two mechanisms: multimodal In-Context Learning (mICL), which separates and aligns visual and textual representations, and a late fusion strategy that injects original visual features into final embeddings. Models are trained end-to-end using contrastive learning on large-scale user interaction data.

**Findings:**
Our investigation reveals that NoteLLM-2 consistently improves recall performance over strong multimodal and LLM-based baselines. We observe better visual-text balance and robustness, particularly on short-content items, though gains depend on vision encoder capacity and introduce modest computational overhead.

---

## Brand-Aware Text Generation with Knowledge-Guided Constraints

**Authors:** Jiawei Liu, Minghao Chen, Rui Zhang, Yuxin Wang

**Abstract:**
This paper investigates the problem of maintaining brand consistency in automatically generated marketing content. The authors propose incorporating brand knowledge and stylistic constraints into language models to ensure generated text aligns with predefined brand attributes such as tone, vocabulary, and messaging intent.

**Methodology:**
The approach encodes brand attributes as structured constraints derived from brand guidelines and auxiliary knowledge sources, which are injected into the generation process via controlled decoding and prompt conditioning.

**Findings:**
Our investigation reveals improved alignment with brand tone and messaging compared to unconstrained generation. We observe reduced stylistic drift across long-form outputs, though effectiveness depends on the completeness of brand knowledge representations.

---

## VisionTrap: Vision-Augmented Trajectory Prediction Guided by Textual Descriptions

**Authors:** Seokha Moon, Hyun Woo, Hongbeen Park, Haeji Jung, Reza Mahjourian, Hyung-gun Chi, Hyerin Lim, Sangpil Kim, Jinkyu Kim

**Abstract:**
This paper investigates improving trajectory prediction for autonomous driving by incorporating visual semantic cues and textual descriptions alongside traditional inputs such as past trajectories and HD maps. The authors propose VisionTrap, a vision-augmented model that uses surround-view camera images and text generated by vision-language models to capture agent behavior and environmental context more effectively.

**Methodology:**
VisionTrap encodes multi-view images into a BEV representation and augments agent embeddings via deformable attention. Textual descriptions generated by a VLM and refined by an LLM are used during training through contrastive learning to guide visual semantic understanding.

**Findings:**
Our investigation reveals consistent improvements in trajectory prediction accuracy across vehicles and pedestrians on the nuScenes dataset. We observe that visual semantics and text-driven guidance reduce miss rates while maintaining real-time inference, though additional preprocessing is required to generate textual supervision.

---

## Entity Retrieval for Answering Entity-Centric Questions

**Authors:** Hassan S. Shavarani, Anoop Sarkar

**Abstract:**
This paper examines limitations of similarity-based retrieval methods in retrieval-augmented question answering, particularly for entity-centric questions. The authors propose Entity Retrieval, which relies on salient entities in a question to directly retrieve corresponding knowledge base articles, rather than searching large passage indexes.

**Methodology:**
The method identifies salient entities in a question, retrieves their corresponding Wikipedia articles, and truncates them to the first W words for augmentation. Performance is evaluated against BM25, DPR, and ANCE on multiple QA datasets using retrieval and answer-quality metrics.

**Findings:**
Our investigation reveals that Entity Retrieval consistently outperforms dense and sparse retrievers on entity-centric datasets while requiring fewer documents. We observe improved efficiency and reduced noise, though performance depends on accurate entity identification and linking.

---

## Sketch2Scene: Automatic Generation of Interactive 3D Game Scenes from User's Casual Sketches

**Authors:** Yongzhi Xu, Yonhon Ng, Yifu Wang, Inkyu Sa, Yunfei Duan, Yang Li, Pan Ji, Hongdong Li

**Abstract:**
This paper addresses the challenge of generating large-scale, interactive 3D scenes from minimal user input. The authors propose a pipeline that transforms casual hand-drawn sketches and optional text prompts into playable 3D game scenes by leveraging diffusion models, visual scene understanding, and procedural generation.

**Methodology:**
The pipeline first generates a 2D isometric reference image using a ControlNet-guided diffusion model, then performs scene understanding to extract terrain, objects, and layouts. These outputs are converted into a 3D scene via procedural generation within a game engine.

**Findings:**
Our investigation reveals that the method produces high-quality, interactive scenes that closely follow user intent. We observe improved controllability and visual coherence compared to prior scene-generation approaches, though errors can accumulate due to the multi-stage pipeline.

---

## Diffusing Wave Microrheology in Polymeric Fluids

**Authors:** George D. J. Phillies

**Abstract:**
This paper examines the validity of the Gaussian approximation commonly used in diffusing wave spectroscopy (DWS) to infer microrheological properties of polymeric and complex fluids. The author argues that probe particle displacements in such media are often non-Gaussian, leading to systematic errors when standard DWS interpretations are applied.

**Methodology:**
The study develops a cumulant-based theoretical analysis of DWS field correlation functions, explicitly accounting for higher-order displacement moments and fluctuations in scattering vectors and path lengths. Analytical derivations are supported by comparisons with prior experimental and simulation studies.

**Findings:**
Our investigation reveals that DWS spectra depend not only on mean-square displacement but also on higher-order moments and path fluctuations. We observe that neglecting these effects can lead to inaccurate microrheological estimates, particularly in viscoelastic polymeric fluids.

---

## Module-wise Adaptive Adversarial Training for End-to-End Autonomous Driving

**Authors:** Tianyuan Zhang, Lu Wang, Jiaqi Kang, Xinwei Zhang, Siyuan Liang, Yuwei Chen, Aishan Liu, Xianglong Liu

**Abstract:**
This paper addresses the vulnerability of end-to-end autonomous driving models to adversarial attacks caused by imperceptible input perturbations. The authors propose Module-wise Adaptive Adversarial Training (MA2T), which jointly considers the interconnected objectives of perception, prediction, and planning modules to improve overall system robustness under both adversarial and natural corruptions.

**Methodology:**
MA2T injects adversarial noise at the inputs of individual modules while optimizing a unified global loss. A dynamic weight accumulation strategy adaptively adjusts module loss weights based on their contribution during training.

**Findings:**
Our investigation reveals consistent robustness gains of 5–10% over standard adversarial training across white-box and black-box attacks. We observe improved closed-loop driving performance in CARLA simulations, though training introduces additional computational overhead.

---

## Wing Optimisation for a Tractor Propeller Driven Micro Aerial Vehicle

**Authors:** Arjun Sharma, Roddam Narasimha

**Abstract:**
This paper investigates the potential benefits of optimizing wing planform and twist for a tractor-propeller micro aerial vehicle (MAV) by explicitly accounting for propeller slip-stream effects. Using the Avion MAV as a case study, the authors analyze how aerodynamic performance metrics such as drag and endurance can be improved at low Reynolds numbers relevant to small UAVs.

**Methodology:**
The study combines lifting-line theory modified for propeller slip-stream with experimental aerofoil data and incompressible flow simulations in OpenFOAM. Wing chord and twist distributions are optimized under fixed and variable lift-coefficient constraints using a Bezier-parameterized optimization framework.

**Findings:**
Our investigation reveals that allowing limited variation in operating lift coefficient enables substantial improvements in endurance, reaching up to 18.6% for ±10% CL variation and over 39% for larger bounds. We observe that most gains arise from reductions in profile drag rather than induced drag, though results depend on aerofoil characteristics and low-fidelity modeling assumptions.

---

## Identifying Latent Disease Factors with Graph-Based Representation Learning

**Authors:** Maria Alvarez, Daniel Ruiz, Sofia Martinez

**Abstract:**
This paper explores the identification of latent disease factors from heterogeneous biomedical data by leveraging graph-based representation learning. The authors propose modeling patients, symptoms, and clinical variables as nodes in a graph to uncover hidden relationships that are not easily captured by traditional statistical methods.

**Methodology:**
The approach constructs a heterogeneous graph and applies graph neural networks with attention mechanisms to learn node embeddings. Clustering and downstream prediction tasks are used to evaluate the quality of the learned latent representations.

**Findings:**
Our investigation reveals that graph-based representations improve the discovery of latent disease factors compared to baseline methods. We observe enhanced interpretability of learned clusters, though performance depends on graph construction choices and data completeness.

---

## Revealing and Mitigating the Local Pattern Shortcuts of Mamba

**Authors:** Wangjie You, Zecheng Tang, Juntao Li, Lili Yao, Min Zhang

**Abstract:**
This paper investigates why the Mamba state-space model performs inconsistently on long-context retrieval tasks despite its linear-time efficiency. The authors show that Mamba relies on local pattern shortcuts, such as positional and n-gram cues, which allow strong performance on fixed templates but hinder generalization to tasks requiring dispersed or dense information retrieval.

**Methodology:**
Controlled synthetic experiments based on the Multi-Query Associative Recall (MQAR) task are used to analyze Mamba's attention-like state behavior. A global selection module using long-range convolution is introduced to inject global context into Mamba's selective update mechanism.

**Findings:**
Our investigation reveals that Mamba's performance gap arises from over-reliance on local shortcuts rather than true recall ability. We observe that the proposed global selection mechanism significantly improves robustness and multi-hop retrieval, increasing performance from near zero to over 80% on high-density tasks.

---

## Relative Optimal Transport

**Authors:** Peter Bubenik, Aaron Elchesen

**Abstract:**
This paper introduces Relative Optimal Transport (ROT), a generalization of classical optimal transport designed to compare probability measures relative to a reference measure. The framework is motivated by applications in topological data analysis, particularly for comparing persistence diagrams where mass creation and deletion must be handled in a principled way.

**Methodology:**
The authors define relative Wasserstein distances using a signed measure framework and develop a dual formulation based on relative Lipschitz functions. Theoretical properties such as metric validity, stability, and existence of optimal plans are formally proven.

**Findings:**
Our investigation reveals that relative optimal transport unifies classical and unbalanced OT under a common framework. We observe that ROT provides stable and interpretable distances for persistence diagrams, while maintaining strong theoretical guarantees absent in standard OT formulations.

---

## A Compact Group Lens Modeled with GIGA-Lens: Enhanced Inference for Complex Systems

**Authors:** F. Urcelay, E. Jullo, L. F. Barrientos, X. Huang, J. Hernandez

**Abstract:**
This paper focuses on efficient modeling of group-scale strong gravitational lens systems in the context of upcoming large astronomical surveys. The authors extend the GIGA-Lens framework to handle complex multi-galaxy lenses using GPU-accelerated Bayesian inference, demonstrating its effectiveness on the compact group lens DES J0248–3955.

**Methodology:**
The approach combines image position constraints with pixel-level surface brightness modeling using a two-stage annealed Sequential Monte Carlo (SMC) sampling strategy. GPU acceleration and sparse pixel masks are employed to efficiently explore a high-dimensional parameter space.

**Findings:**
Our investigation reveals that the enhanced GIGA-Lens framework can constrain a 29-parameter group-scale lens model within minutes using ground-based data. We observe accurate recovery of lens properties and evidence for a double source-plane system, though results remain sensitive to model assumptions and priors.

---

## A Survey on Retrieval-Augmented Generation and Graph-Based Reasoning for Large Language Models

**Authors:** Yujuan Ding, Wenqi Fan, Liangbo Ning, Shijie Wang, Hengyun Li, Dawei Yin, Tat-Seng Chua, Qing Li

**Abstract:**
This paper provides a comprehensive survey of retrieval-augmented generation (RAG) methods, with particular emphasis on graph-based reasoning and their integration with large language models. The authors review how structured knowledge sources such as knowledge graphs, document graphs, and entity networks are leveraged to improve factual grounding, multi-hop reasoning, and scalability in generation tasks.

**Methodology:**
The survey categorizes RAG approaches into vector-based, graph-based, and hybrid methods, comparing their retrieval mechanisms, reasoning strategies, and system architectures. Representative models and benchmarks are systematically analyzed across QA, summarization, and knowledge-intensive tasks.

**Findings:**
Our investigation reveals that graph-based RAG methods consistently improve multi-hop reasoning and reduce hallucinations compared to text-only retrieval. We observe open challenges in graph construction cost, dynamic updates, and evaluation standardization.

---

## On the Structure of Some One-Generator Nilpotent Braces

**Authors:** Martyn R. Dixon, Leonid A. Kurdachenko, Igor Ya. Subbotin

**Abstract:**
This paper studies the internal structure of left braces generated by a single element under various notions of nilpotency. Motivated by connections between braces and set-theoretic solutions of the Yang–Baxter equation, the authors focus on Smoktunowicz-nilpotent and ⋆-nilpotent braces and provide explicit structural descriptions for low ⋆-nilpotency classes.

**Methodology:**
The authors develop an algebraic framework based on ⋆-central series and nilpotency conditions, and construct explicit brace models D(1,2) and D(1,3). Formal proofs use combinatorial identities, inductive arguments, and structural homomorphisms to classify one-generator cases.

**Findings:**
Our investigation reveals that one-generator ⋆-nilpotent braces admit strong structural constraints and can often be expressed as epimorphic images of explicitly constructed model braces. We observe that for ⋆-nilpotency class three, the second derived brace is necessarily abelian, providing a clear classification boundary.

---

## Design and Characterization of Large-Scale Data Pipelines for Machine Learning Systems

**Authors:** Rakesh Mehta, Ananya Iyer, Pradeep Kumar

**Abstract:**
This paper examines the architectural design and performance characteristics of large-scale data pipelines used in modern machine learning systems. The authors focus on challenges related to data ingestion, preprocessing, storage, and orchestration, particularly in environments where heterogeneous data sources and high throughput requirements are present.

**Methodology:**
The study evaluates modular pipeline architectures using batch and streaming data flows, supported by distributed processing frameworks. Empirical analysis is conducted on latency, fault tolerance, and scalability under varying workloads.

**Findings:**
Our investigation reveals that decoupled, modular pipeline designs significantly improve scalability and fault isolation. We observe that while streaming pipelines reduce end-to-end latency, they introduce higher operational complexity compared to batch-oriented systems.

---

## Bose–Einstein Condensation of Five α Clusters in ²⁰Ne and Supersolidity

**Authors:** S. Ohkubo, J. Takahashi, Y. Yamanaka

**Abstract:**
This paper investigates recently observed five-α cluster states in ²⁰Ne and argues that they constitute a Bose–Einstein condensate of α clusters. Using a field-theoretical framework, the authors connect these states to collective excitations analogous to phonons and rotons, and explore their interpretation as exhibiting supersolid behavior with both superfluid and crystalline characteristics.

**Methodology:**
The study employs a superfluid cluster model based on effective field theory, solving coupled Gross–Pitaevskii, Bogoliubov–de Gennes, and Nambu–Goldstone equations. Energy spectra and rotational bands are calculated and compared with experimental data for ²⁰Ne, ¹⁶O, and ¹²C.

**Findings:**
Our investigation reveals that the observed five-α states in ²⁰Ne are consistent with α-cluster BEC behavior. We observe the emergence of rotational roton bands with large moments of inertia, supporting a dual superfluid–crystalline interpretation and providing a potential experimental signature of nuclear supersolidity.

---

## WebLists: Extracting Structured Information from Complex Interactive Websites Using Executable LLM Agents

**Authors:** Arth Bohra, Manvel Saroyan, Danil Melkozerov, Vahe Karufanyan, Gabriel Maher, Pascal Weinberger, Artem Harutyunyan, Giovanni Campagna

**Abstract:**
This paper introduces WebLists, a benchmark designed to evaluate web agents on large-scale, schema-bound data extraction tasks from live, interactive websites. The authors highlight that existing web agent benchmarks overemphasize navigation and question answering, while failing to measure structured data extraction performance required in real-world research and business workflows.

**Methodology:**
The authors propose BardeenAgent, an executable web agent that operates in a record–replay paradigm. The agent records interactions using generalizable CSS selectors and converts them into executable programs that scale extraction across paginated lists with minimal LLM calls.

**Findings:**
Our investigation reveals that existing agents achieve low recall (≤30%) on structured extraction tasks. We observe that BardeenAgent improves recall by 36% while maintaining over 72% precision and reducing cost per extracted row by nearly 3×.

---

## Reinforcement Learning from User Feedback

**Authors:** Eric Han, Jun Chen, Karthik Abinav Sankararaman, Xiaoliang Peng, Tengyu Xu, Eryk Helenowski, Kaiyan Peng, Mrinal Kumar, Sinong Wang, Han Fang, Arya Talebzadeh

**Abstract:**
This paper proposes Reinforcement Learning from User Feedback (RLUF), a framework for aligning large language models using implicit, real-world user signals rather than expert-annotated preferences. The authors focus on lightweight binary feedback such as emoji reactions and argue that these signals better reflect authentic user satisfaction at scale compared to traditional RLHF.

**Methodology:**
The approach trains a user-signal reward model P[Love] on binary user feedback and integrates it into a multi-objective reinforcement learning framework alongside helpfulness and safety rewards. Policy optimization is performed using a mixture-of-judges strategy with controlled reward weighting.

**Findings:**
Our investigation reveals that optimizing with user feedback increases positive user reactions by up to 28% in large-scale A/B tests. We observe clear trade-offs with helpfulness and reward-hacking behaviors, highlighting the need for careful multi-objective balancing.

---

## AutoSchemaKG: Autonomous Knowledge Graph Construction through Dynamic Schema Induction from Web-Scale Corpora

**Authors:** Jiaxin Bai, Wei Fan, Qi Hu, Qing Zong, Chunyang Li, Hong Ting Tsang, Hongyu Luo, Yauwai Yim, Haoyu Huang, Xiao Zhou, Feng Qin, Tianshi Zheng, Xi Peng, Xin Yao, Huiwen Yang, Leijie Wu, Yi Ji, Gong Zhang, Renhai Chen, Yangqiu Song

**Abstract:**
This paper proposes AutoSchemaKG, a fully automated framework for constructing large-scale knowledge graphs without relying on predefined schemas. The authors leverage large language models to jointly extract entity–entity, entity–event, and event–event relations while dynamically inducing conceptual schemas that organize entities, events, and relations. The approach is validated by constructing the ATLAS family of billion-scale knowledge graphs from web-scale corpora.

**Methodology:**
The framework uses a multi-stage LLM-based pipeline for triple extraction followed by schema induction via conceptualization prompts that abstract entities, events, and relations. The resulting graphs integrate entity, event, and concept nodes and are evaluated on multi-hop QA, information preservation, and factuality benchmarks.

**Findings:**
Our investigation reveals that AutoSchemaKG achieves over 95% precision in triple extraction and high semantic alignment with human-crafted schemas without manual intervention. We observe consistent improvements of 12–18% on multi-hop QA and enhanced LLM factuality, though construction requires substantial computational resources.

---

## Recycling the Web: A Method to Enhance Pre-training Data Quality and Quantity for Language Models

**Authors:** Thao Nguyen, Yang Li, Olga Golovneva, Luke Zettlemoyer, Sewoong Oh, Ludwig Schmidt, Xian Li

**Abstract:**
This paper addresses the emerging "data wall" in large language model pre-training by proposing a framework to recycle low-quality web documents rather than discarding them. The authors introduce REWIRE, a guided rewriting pipeline that transforms moderately filtered web data into high-quality synthetic text, enabling more efficient scaling without relying on additional raw data sources.

**Methodology:**
The REWIRE pipeline applies LLM-guided rewriting with chain-of-thought prompting to moderate-quality Common Crawl documents, followed by classifier-based filtering. Models are trained on mixtures of raw and rewritten data and evaluated across multiple scales using the DCLM benchmark.

**Findings:**
Our investigation reveals consistent performance gains of up to 2.5 percentage points across 22 tasks compared to training on high-quality raw data alone. We observe that over 80% of useful synthetic data originates from documents that would otherwise be discarded, effectively doubling usable training tokens.

---

## Planning with Reasoning using Vision Language World Model

**Authors:** Delong Chen, Théo Moutakanni, Willy Chung, Yejin Bang, Ziwei Ji, Allen Bolourchi, Pascale Fung

**Abstract:**
This paper proposes the Vision Language World Model (VLWM), a framework for high-level planning that represents world dynamics directly in natural language rather than raw visual space. The authors aim to bridge perception and reasoning by learning abstract action–state transitions from large-scale instructional and egocentric videos, enabling interpretable and long-horizon planning.

**Methodology:**
The approach compresses videos into hierarchical Trees of Captions, then uses iterative LLM Self-Refine to extract goal descriptions, actions, and world state changes. VLWM supports fast System-1 planning via autoregressive rollout and System-2 planning via cost minimization using a self-supervised language-based critic.

**Findings:**
Our investigation reveals that VLWM achieves state-of-the-art performance on Visual Planning for Assistance and RoboVQA benchmarks. We observe substantial gains from System-2 reasoning in human preference evaluations, though the framework requires heavy preprocessing and large-scale video data.

---

## Knowledge Extraction on Semi-Structured Content: Does It Remain Relevant for Question Answering in the Era of LLMs?

**Authors:** Kai Sun, Yin Huang, Srishti Mehra, Mohammad Kachuee, Xilun Chen, Renjie Tao, Zhaojiang Lin, Andrea Jessee, Nirav Shah, Alex Betty, Yue Liu, Anuj Kumar, Wen-tau Yih, Xin Luna Dong

**Abstract:**
This paper examines whether structured knowledge extraction remains useful for question answering as Large Language Models increasingly rely on unstructured text understanding. The authors extend the WebSRC benchmark by adding triple extraction annotations and whole webpage data to evaluate LLM performance. Their investigation reveals that while LLMs achieve high QA accuracy, explicit knowledge extraction still provides measurable benefits, especially for smaller models and noisy web content.

**Methodology:**
The authors evaluate zero-shot, few-shot, fine-tuned, and script-based triple extraction methods using multiple LLMs on cleaned and full webpages. QA performance is measured with and without augmenting extracted triples. Multi-task fine-tuning combines QA and extraction objectives.

**Findings:**
We observe that triple extraction accuracy drops sharply on real-world webpages despite strong QA results. Augmenting content with extracted triples improves QA, particularly for smaller models. The study shows that knowledge extraction remains beneficial but is not yet reliable at web scale.

---

## Development of an Automated Web Application for Efficient Web Scraping: Design and Implementation

**Authors:** Alok Dutta, Nilanjana Roy, Rhythm Sen, Sougata Dutta, Prabhat Das

**Abstract:**
This paper presents the design and implementation of an automated, user-friendly web application aimed at simplifying web scraping for non-technical users. The system decomposes web scraping into fetching, extraction, and execution stages, enabling users to retrieve, refine, and store web data efficiently through a graphical interface.

**Methodology:**
The application is implemented using Python with Flask for deployment, BeautifulSoup and lxml for HTML parsing, and Selenium for dynamic content when required. MongoDB is integrated for user management and data persistence, and performance is analyzed using mathematical models of runtime and memory usage.

**Findings:**
Our investigation reveals an average website scrapability rate of 79.4% across 20 categories, with static informative sites achieving the highest success. We observe that while the tool incurs higher memory usage than lightweight libraries, added features such as data persistence and user interaction improve practical usability.

---

## Leveraging Large Language Models for Web Scraping

**Authors:** Aman Ahluwalia, Suhrud Wani

**Abstract:**
This paper investigates the use of Large Language Models combined with Retrieval-Augmented Generation (RAG) to improve web scraping accuracy from unstructured and dynamic webpages. The authors argue that traditional rule-based crawlers struggle with semantic understanding, dynamic content, and hallucination issues, and propose a modular RAG-based extraction pipeline.

**Methodology:**
The framework renders webpages to HTML, applies recursive text chunking, embeds chunks into a FAISS vector store, and retrieves top-k relevant segments for extraction. An ensemble of LLMs (GPT-4, Mixtral, LLaMA-3) is used with voting-based ranking to reduce hallucinations and improve extraction reliability.

**Findings:**
Our investigation reveals that RAG-based scraping improves semantic accuracy and robustness compared to traditional crawlers. We observe reduced hallucination and better handling of dynamic content, though performance depends on effective chunking, retrieval quality, and ensemble coordination.

---

## Energy Barriers for Boundary Nucleation in a Two-Well Model Without Gauge Invariances

**Authors:** Antonio Tribuzio, Konstantinos Zemas

**Abstract:**
This paper studies energy scaling laws for martensitic phase nucleation confined to a half-space. The authors analyze how boundary constraints and the orientation of rank-1 connections influence nucleation energy barriers compared to bulk nucleation.

**Methodology:**
The authors formulate a variational two-well elastic energy model without gauge invariance and derive lower and upper energy bounds using covering arguments, reflection techniques, and scaling analysis.

**Findings:**
The study shows that boundary nucleation can lower energy barriers when the rank-1 direction is normal to the boundary. Otherwise, scaling matches bulk nucleation behavior, revealing a clear orientation-dependent dichotomy.
