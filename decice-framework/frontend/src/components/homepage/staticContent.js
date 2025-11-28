// Static fallback content used when the remote content API is not reachable.
// These structures intentionally mirror the API responses from the DECICE
// content service so that existing UI code can consume them without changes.

export const FALLBACK_EVENTS = {
    source: "events",
    payload: {
        "fetched_at": "2025-11-25T14:57:28.889296",
        "events": [{
                "title": "DECICE Final Project Webinar",
                "date": "12.11.2025",
                "organiser": "DECICE consortium",
                "location": "online",
                "link": "https://www.decice.eu/project-news/decice-final-webinar/",
                "section": null
            },
            {
                "title": "From Connected to Autonomous Cars: Intelligent Transportation Systems Workshop (MarUn/BIG TRI annual WS)",
                "date": "TBA",
                "organiser": "MarUn / BIG TRI",
                "location": "Turkey (Istanbul)",
                "link": "https://venit.org/v2x_workshop/%20",
                "section": "past"
            },
            {
                "title": "2nd From Connected to Autonomous Cars: Intelligent Transportation Systems Workshop”  (MarUn/BIG TRI annual WS)",
                "date": "TBA",
                "organiser": "MarUn / BIG TRI",
                "location": "Turkey (Istanbul)",
                "link": "https://events.gwdg.de/event/308/",
                "section": "past"
            },
            {
                "title": "SC24 (Supercomputing Conference) Workshops",
                "date": "TBA",
                "organiser": "TBA |",
                "location": "TBA",
                "link": null,
                "section": "past"
            },
            {
                "title": "CARO workshop at HiPEAC25 conference",
                "date": "20.-21.01.2025",
                "organiser": "DECICE / ACES projects",
                "location": "Spain (Barcelona)",
                "link": "https://www.decice.eu/project-news/caro-workshop-at-hipeac25-conference/",
                "section": "past"
            },
            {
                "title": "Exploring the Computing Continuum with DECICE and Fluidos",
                "date": "27.09.2024",
                "organiser": "DECICE and Fluidos project",
                "location": "online",
                "link": "https://www.decice.eu/project-news/decice-and-fluidos-webinar/",
                "section": "past"
            },
            {
                "title": "19th Conference on Computer Science and Intelligence Systems (FedCSIS 2024)",
                "date": "08.–11.09.2024",
                "organiser": "University of Belgrade Faculty of Organisational Science; Polskie Towarzystwo Informatyczne; iBS PAN; Faculty of Mathematics and Information Science, IEEE Comupter Society – Poland Section Chapte r",
                "location": "Serbia (Belgrade)",
                "link": "https://fedcsis.org",
                "section": "past"
            },
            {
                "title": "Teratec Forum 2024",
                "date": "29.–30.05.2024",
                "organiser": "Teratec, Infopro Digital",
                "location": "France (Paris)",
                "link": "https://www.forumteratec.com/en/",
                "section": "past"
            },
            {
                "title": "WAICF - World AI Cannes Festival 2024",
                "date": "08.–10.02.2024",
                "organiser": "EuropIA institute; City of Cannes; Palais des Festivals et des Congrès",
                "location": "France (Cannes)",
                "link": "https://www.worldaicannes.com/",
                "section": "past"
            },
            {
                "title": "CLOUD DAY",
                "date": "03.02.2024",
                "organiser": "Forschung Burgenland | Location: Austria (Eisenstadt)",
                "location": null,
                "link": "https://twitter.com/IGI_Smalls/status/1722561490496991453",
                "section": "past"
            },
            {
                "title": "HIPEAC 2024",
                "date": "17.–19.01.2024",
                "organiser": "High Performance, Edge And Cloud computing – HiPEAC project",
                "location": "Germany (Munich)",
                "link": "https://www.hipeac.net/2024/munich/#/",
                "section": "past"
            },
            {
                "title": "Cognitive Cloud Continuum Ecosystems: Theory and Practice",
                "date": "03.–06.01.2024",
                "organiser": "ASSIST-IoT and aerOS projects",
                "location": "Hawaii (Honolulo)",
                "link": "https://assist-iot.eu/2023/04/17/assist-iot-minitrack-in-hicss57-call-for-papers/",
                "section": "past"
            },
            {
                "title": "EuroHPC User Day",
                "date": "11.12.2023",
                "organiser": "The European High Performance Computing Joint Undertaking (EuroHPC JU)",
                "location": "Belgium (Brussels)",
                "link": "https://eurohpc-ju.europa.eu/news-events/events/eurohpc-user-day-2023-12-11_en",
                "section": "past"
            },
            {
                "title": "23rd International Conference on Intelligent Systems Design and Applications (ISDA’23)",
                "date": "11.–13.12.2023",
                "organiser": "ISDA 2023",
                "location": "Switzerland (Olten), Portugal (Porto), Lithuania (Vilnius), India (Kochi)",
                "link": "http://www.mirlabs.org/isda23/",
                "section": "past"
            },
            {
                "title": "Digital Platforms for the Cloud-Edge-IoT, Innovation through Open Source and Software",
                "date": "04.12.2023",
                "organiser": "EU CLoud Edge | Location: Belgium (Brussels) | online",
                "location": null,
                "link": "https://eucloudedgeiot.eu/event/2024calls_infosession/",
                "section": "past"
            },
            {
                "title": "Digital Twins: Solving Pain Points for Connectivity and Accelerating Profitability",
                "date": "16.11.2023",
                "organiser": "Sand Technologies",
                "location": "online",
                "link": "https://www.sandtech.com/webinar/digital-twins-solving-pain-points-for-connectivity-and-accelerating-profitability/",
                "section": "past"
            },
            {
                "title": "the Next Generation Internet Forum",
                "date": "16.11.2023",
                "organiser": "Sand Technologies",
                "location": "online",
                "link": "https://www.sandtech.com/webinar/digital-twins-solving-pain-points-for-connectivity-and-accelerating-profitability/",
                "section": "past"
            },
            {
                "title": "Giving Energy an Edge - Showcasing the Edge to Cloud Continuum in Energy",
                "date": "10.11.2023",
                "organiser": "EU CLoud Edge",
                "location": "Online",
                "link": "https://eucloudedgeiot.eu/event/giving-energy-edge-showcase/",
                "section": "past"
            },
            {
                "title": "SC23 (Supercomputing Conference) Workshops",
                "date": "12.–13.11.2023",
                "organiser": "The International Conference for High Performance Computing, Networking, Storage, and Analysis",
                "location": "USA (Denver)",
                "link": "https://sc23.supercomputing.org/program/workshops/",
                "section": "past"
            },
            {
                "title": "Consortium Meeting",
                "date": "06.–08.11.2023",
                "organiser": "SYNYO",
                "location": "Austria (Vienna)",
                "link": "https://european-big-data-value-forum.eu/",
                "section": "past"
            },
            {
                "title": "EBDVF 2023 – European BigData Value Forum",
                "date": "25-27.10.2023",
                "organiser": "BDV Big Data Value Association",
                "location": "Spain (Valencia)",
                "link": "https://european-big-data-value-forum.eu/",
                "section": "past"
            },
            {
                "title": "eSAAM 2023 on Cloud-to-Edge Continuum",
                "date": "17.10.2023",
                "organiser": "ECLIPSE Foundation |",
                "location": "Germany (Ludwigsburg )",
                "link": "https://events.eclipse.org/2023/esaam2023/",
                "section": "past"
            },
            {
                "title": "NEXUS Forum",
                "date": "05.–06.10.2023",
                "organiser": "Open Nebula",
                "location": "Belgium (Brussels)",
                "link": "https://opennebula.io/innovation/nexusforum2023/",
                "section": "past"
            },
            {
                "title": "EuroHPC JU Information Day for AI on Supercomputers",
                "date": "26.09.2023",
                "organiser": "The European High Performance Computing Joint Undertaking (EuroHPC JU)",
                "location": null,
                "link": "https://eurohpc-ju.europa.eu/news-events/events/eurohpc-ju-information-day-ai-supercomputers-virtual-2023-09-26_en",
                "section": "past"
            },
            {
                "title": "IOT TECH EXPO Europe",
                "date": "26.–27.09.2023",
                "organiser": "TechEx",
                "location": "Netherlands (Amsterdam)",
                "link": "https://www.iottechexpo.com/europe/",
                "section": "past"
            },
            {
                "title": "The 1st International Workshop on Machine Learning for Autonomic System Operations in the Device-Edge-Cloud Continuum (MLSysOps 2023)",
                "date": "25.09.2023",
                "organiser": "EWSN 2023 Conference; University of Calabria",
                "location": "Italy (Rende)",
                "link": "https://events.dimes.unical.it/mlsysops2023/",
                "section": "past"
            },
            {
                "title": "Advancing towards the Cloud, Edge, and IoT Continuum: Insights and Impacts",
                "date": "25.09.2023",
                "organiser": "EU Cloud Edge IoT.eu",
                "location": "online",
                "link": "https://eucloudedgeiot.eu/event/advancing-towards-cei-continuum/?utm_source=linkedin.com&utm_medium=social&utm_campaign=08082023_y1event_savethedate",
                "section": "past"
            },
            {
                "title": "Capitalising on Cloud-Edge-IoT: Building your next product, finding your next market opportunity",
                "date": "20.09.2023",
                "organiser": "EU Cloud Edge IoT.eu",
                "location": "online",
                "link": "https://eucloudedgeiot.eu/event/webinar-capitalising-cei-open-calls/",
                "section": "past"
            },
            {
                "title": "IEEE COINS 2023: IEEE International Conference on Omni-Layer Intelligent Systems",
                "date": "23.–25.07.2023",
                "organiser": "IEEE",
                "location": "Germany (Berlin)",
                "link": "http://coinsconf.com",
                "section": "past"
            },
            {
                "title": "Use Case Requirements Workshop #2",
                "date": "13.07.2023",
                "organiser": "TOP-IX",
                "location": "online",
                "link": "https://www.decice.eu/project-news/requirements-workshop2/",
                "section": "past"
            },
            {
                "title": "Cloud-Edge-IoT Innovations in Manufacturing: Unveiling Market Insights an Use Cases",
                "date": "10.07.2023",
                "organiser": "UNLOCK-CEI and more",
                "location": "online",
                "link": "https://eu01web.zoom.us/webinar/register/WN__gFpCpNFSMaLc4meoofcYQ#/registration",
                "section": "past"
            },
            {
                "title": "VOLCANO Webinar",
                "date": "05.07.2023",
                "organiser": "DECICE (OEHI)",
                "location": "online",
                "link": "https://www.decice.eu/project-news/volcano-webinar/",
                "section": "past"
            },
            {
                "title": "ETSI IoT Conference 2023 (ETSI IoT Week 2023)",
                "date": "04.–06.07.2023",
                "organiser": "ETSI",
                "location": "France (Sophia Antipolis)",
                "link": "https://www.etsi.org/events/2208-etsi-iot-conference-2023",
                "section": "past"
            },
            {
                "title": "PASC23",
                "date": "26.–28.06.2023",
                "organiser": "Association for Computing Machinery; sighpc; cscs",
                "location": "Switzerland (Davos)",
                "link": "https://pasc23.pasc-conference.org/",
                "section": "past"
            },
            {
                "title": "DATA WEEK 23",
                "date": "13.–15.06.2023",
                "organiser": "BDVA and EUHubs4Data, hosted by/collaboration with RISE (Research Institutes of Sweden)",
                "location": "Sweden (Luleå)",
                "link": "https://www.bdva.eu/data-week-2023",
                "section": "past"
            },
            {
                "title": "TREXworkshop \"Code Tuning for the Exascale\"",
                "date": "05.–07.06.2023",
                "organiser": "TREX Project",
                "location": "Slovakia (Bratislava)",
                "link": "https://trex-coe.eu/events/trex-workshop-code-tuning-exascale?utm_source=linkedin.com&utm_medium=social&utm_campaign=trexworkshop_ppccampaign",
                "section": "past"
            },
            {
                "title": "INFN Workshop sul Calcolo",
                "date": "22.–26.05.2023",
                "organiser": "Indico",
                "location": "Italy (Savona)",
                "link": "https://agenda.infn.it/event/34683/",
                "section": "past"
            },
            {
                "title": "HPC-IODC: HPC I/O in the Data Center Workshop",
                "date": "25.05.2023",
                "organiser": "ISC HPC",
                "location": "Germany (Hamburg) ISC-HPC",
                "link": "https://hps.vi4io.org/events/2023/iodc",
                "section": "past"
            },
            {
                "title": "Computing Continuum and the Role of AI as a complementary technology: European market forecast and Insights",
                "date": "24.05.2023",
                "organiser": "EUCloudEdgeIoT.eu",
                "location": "Online",
                "link": "https://us02web.zoom.us/webinar/register/1816819945560/WN_ltYXyWLRTXGmWB8ZdWkopA#/registration",
                "section": "past"
            },
            {
                "title": "ISC HPC 2023",
                "date": "21.–25.05.2023",
                "organiser": "ISC HPC",
                "location": "Germany (Hamburg)",
                "link": "https://www.isc-hpc.com/",
                "section": "past"
            },
            {
                "title": "Global IoT Summit 2023",
                "date": "19.–20.05.2023",
                "organiser": "Springer; Lecture Notes in Computer Science",
                "location": "Germany (Berlin)",
                "link": "https://globaliotsummit.org/",
                "section": "past"
            },
            {
                "title": "Concertation and Consultation on Computing Continuum (EC Cluster 4)",
                "date": "10.–11.05.20.23",
                "organiser": "EU Cloud Edge IoT.eu",
                "location": "Belgium (Brussels)",
                "link": "https://eucloudedgeiot.eu/concertation-and-consultation-on-computing-continuum-from-cloud-to-edge-to-iot/",
                "section": "past"
            },
            {
                "title": "The European Identity and Cloud Conference",
                "date": "09.–13.05.2023",
                "organiser": "HaDEA",
                "location": "Germany (Berlin)",
                "link": "https://hadea.ec.europa.eu/news/european-identity-and-cloud-conference-2023-meet-hadea-managed-projects-working-digital-services-2023-05-08_en",
                "section": "past"
            },
            {
                "title": "CF2023 (Computing Fontiers)",
                "date": "09.–11.05.2023",
                "organiser": "CF (UNIBO)",
                "location": "Italy (Bologna)",
                "link": "https://www.computingfrontiers.org/2023/ssEUproj.html",
                "section": "past"
            },
            {
                "title": "Use Case Requirements Workshop",
                "date": "20.04.2023",
                "organiser": "TOP-IX",
                "location": "online",
                "link": "https://www.decice.eu/project-news/requirements-workshop/",
                "section": "past"
            },
            {
                "title": "KubeCon 2023",
                "date": "18.–21.04.2023",
                "organiser": "KubeCon; CloudNativCon",
                "location": "Netherlands (Amsterdam)",
                "link": "https://events.linuxfoundation.org/kubecon-cloudnativecon-europe/",
                "section": "past"
            },
            {
                "title": "HPCAI Advisory Council",
                "date": "03.–06.04.2023",
                "organiser": "HPC Advisory Council",
                "location": "Swiss (Lugano)",
                "link": "https://www.hpcadvisorycouncil.com/events/2023/swiss-conference/",
                "section": "past"
            },
            {
                "title": "Kick Off Meeting",
                "date": "28.–29.03.2023",
                "organiser": "GWDG |",
                "location": "Germany (Göttingen)",
                "link": null,
                "section": "past"
            },
            {
                "title": "KISSKI Symposium",
                "date": "21.–23.03.2023",
                "organiser": "GWDG",
                "location": "Germany (Göttingen)",
                "link": "https://kisski.gwdg.de/ueber-uns/konsortium/",
                "section": "past"
            },
            {
                "title": "EuroHPC Summit 2023",
                "date": "20.–23.03.2023",
                "organiser": "EuroHPC",
                "location": "Sweden (Goethenburg)",
                "link": "https://www.eurohpcsummit.eu/",
                "section": "past"
            },
            {
                "title": "WAICF - World AI Cannes Festival 2023",
                "date": "09.–11.02.2023",
                "organiser": "EuropIA institute; City of Cannes; Palais des Festivals et des Congrès",
                "location": "France (Cannes)",
                "link": "https://www.worldaicannes.com/",
                "section": "past"
            },
            {
                "title": "Horizon Europe Info Day",
                "date": "30.01.2023",
                "organiser": "European Commission; EU IoT; EUCloudEdgeIoT",
                "location": "online",
                "link": "https://eucloudedgeiot.eu/horizon-europe-info-day/",
                "section": "past"
            },
            {
                "title": "Secure Data Processing",
                "date": "16.01.2023",
                "organiser": "GWDG |",
                "location": "Germany",
                "link": "https://events.gwdg.de/event/308/",
                "section": "past"
            },
            {
                "title": "Kick Off Meeting",
                "date": "17.11.2022",
                "organiser": "GWDG |",
                "location": "online",
                "link": null,
                "section": "past"
            }
        ]
    },
};

export const FALLBACK_CONSORTIUM = {
    source: "consortium",
    payload: {
        "fetched_at": "2025-11-25T14:57:26.880470",
        "partners": [{
                "name": "Georg-August-Universität Göttingen Stiftung Öffentlichen Rechts",
                "description": "The University of Göttingen is an internationally renowned research university. Founded in 1737 in the Age of Enlightenment, the University is committed to the values of social responsibility of science, democracy, tolerance and justice. It offers a comprehensive range of subjects across 13 faculties: in the natural sciences, humanities, social sciences and medicine. With about 30,000 students and more than 210 degree programmes, the University is one of the largest in Germany. The mission of the Institute of Computer Science that supports the DECICE project is research and teaching on theoretical, applied and practical computer science.",
                "logo": "https://www.decice.eu/wp-content/uploads/2022/09/01-GEORG-AUGUST-UNIVERSITAT-GOTTINGEN-STIFTUNG-OFFENTLICHEN-RECHTS-Logo-200x126-1.png",
                "links": [
                    { "type": "home", "label": "Home", "url": "https://www.uni-goettingen.de/" },
                    { "type": "twitter", "label": "Twitter", "url": "https://twitter.com/unigoettingen" },
                    { "type": "facebook", "label": "Facebook", "url": "https://www.facebook.com/georgiaaugusta" },
                    { "type": "instagram", "label": "Instagram", "url": "https://twitter.com/unigoettingen" },
                    { "type": "youtube", "label": "Youtube", "url": "https://www.youtube.com/channel/UCzg-z2TL0Ks4Efz5o0z7AxQ" },
                    { "type": "linkedin", "label": "Linkedin", "url": "https://www.linkedin.com/school/-university-of-goettingen/" }
                ]
            },
            {
                "name": "Gesellschaft für Wissenschaftliche Datenverarbeitung MBH Göttingen",
                "description": "The GWDG is a service organization which works in conjunction with the University of Göttingen and the Max Planck Society as a data and IT service center.  It also carries out independent research in the field of computer science and provides support in preparing future professionals for a career in information technology.",
                "logo": "https://www.decice.eu/wp-content/uploads/2022/09/02-GESELLSCHAFT-FUR-WISSENSCHAFTLICHE-DATENVERARBEITUNG-MBH-GOTTINGEN-1-Logo-200x126-1.png",
                "links": [
                    { "type": "home", "label": "Home", "url": "https://www.gwdg.de/" },
                    { "type": "twitter", "label": "Twitter", "url": "https://twitter.com/gwdg" },
                    { "type": "facebook", "label": "Facebook", "url": "https://www.facebook.com/GWDGinfo/" },
                    { "type": "linkedin", "label": "Linkedin", "url": "https://www.linkedin.com/company/gwdg---gesellschaft-f-r-wissenschaftliche-datenverarbeitung-mbh-g-ttingen/" }
                ]
            },
            {
                "name": "E4 Computer Engineering SPA",
                "description": "E4 Computer Engineering creates and provides hardware and software solutions for High Performance Computing, High Performance Data Analytics, Artificial Intelligence, Deep Learning and Virtualization. The growth of our company over recent years has enabled us to employ various open source technologies such as OpenStack, Kubernetes and CI / CD tools in our products. VISION We want to become the leading supplier of hardware and software solutions, focused on technological innovation, with the aim of helping our clients to grow their businesses through the transformation and optimization of their IT systems. MISSION Our goal is to make complex technologies simple. With passion and competence we implement and integrate the most advanced information technologies to achieve the best infrastructural performance possible, in computing, storage and networking, and excel in the development of innovative, flexible and safe solutions. We produce technologically advanced solutions, from first analysing your requirements, to eventually providing after-sales services, including complete support for all our clients.",
                "logo": "https://www.decice.eu/wp-content/uploads/2022/09/03-E-4-COMPUTER-ENGINEERING-SPA-White-1-Logo-200x126-1.png",
                "links": [
                    { "type": "home", "label": "Home", "url": "http://www.e4company.com/" },
                    { "type": "twitter", "label": "Twitter", "url": "https://twitter.com/e4company" },
                    { "type": "linkedin", "label": "Linkedin", "url": "https://www.linkedin.com/company/e4-computer-engineering-spa/" }
                ]
            },
            {
                "name": "Kungliga Tekniska Hoegskolan",
                "description": "The PDC Center for High Performance Computing at the KTH Royal Institute of Technology is a leading provider of high-performance computing (HPC) services for academic as well as commercial research and development efforts in Sweden. PDC’s e-infrastructure services are based on the computing capabilities of HPC and private cloud systems as well as various storage resources including a large-scale Lustre file system. The main HPC system is Dardel, an HPE Cray EX with an expected peak performance of about 13.5 petaflops. PDC’s service portfolio also includes assistance from application and systems experts. PDC is involved in various research software development projects, most notably GROMACS, Neko, and VeloxChem. Furthermore, PDC is an active member of major international HPC infrastructure projects (e.g., PRACE) as well as various exascale research projects, such as the PDC-led BioExcel Centre of Excellence for Biomolecular Research.",
                "logo": "https://www.decice.eu/wp-content/uploads/2022/09/04-KUNGLIGA-TEKNISKA-HOEGSKOLAN-1-Logo-200x126-1.png",
                "links": [
                    { "type": "home", "label": "Home", "url": "https://www.pdc.kth.se/" },
                    { "type": "facebook", "label": "Facebook", "url": "https://www.facebook.com/KTHuniversity" },
                    { "type": "twitter", "label": "Twitter", "url": "https://twitter.com/KTHuniversity" },
                    { "type": "linkedin", "label": "Linkedin", "url": "https://www.linkedin.com/company/pdc-center-for-high-performance-computing-at-kth" }
                ]
            },
            {
                "name": "University of Stuttgart",
                "description": "The High-Performance Computing Center Stuttgart (HLRS) is a research and service institution affiliated to the University of Stuttgart (USTUTT). HLRS has been the first and is presently one of the three large-scale national supercomputing centres in Germany. Consequently, it is one of the leading members of the German supercomputing activities, which are organised by the Gauss Centre for Supercomputing (GCS). HLRS offers its services to academia and industry and thus, concentrates on solution-oriented development and early product integration. HLRS focuses on excellent research in High-Performance Computing, High-Performance Data Analytics and adjuvant technologies such as AI, Cloud Computing, and Quantum Computing. The world leading experience of HLRS is complemented by supporting users in parallel programming (e.g. via the annual Workshop on Sustained Simulation Performance), by developing productivity tools and libraries, by applying software engineering methods within the HPC domain and by enhancing system management software for HPC, HPDA, and Cloud Computing.",
                "logo": "https://www.decice.eu/wp-content/uploads/2022/09/05-University-of-Stuttgart-1-Logo-200x126-1.png",
                "links": [
                    { "type": "home", "label": "Home", "url": "https://www.hlrs.de/" },
                    { "type": "twitter", "label": "Twitter", "url": "https://twitter.com/HLRS_HPC" },
                    { "type": "linkedin", "label": "Linkedin", "url": "https://de.linkedin.com/company/hlrs---high-performance-computing-center-stuttgart" },
                    { "type": "youtube", "label": "Youtube", "url": "https://www.youtube.com/channel/UCqXh8lDnOweUKRCe-fasJcw" }
                ]
            },
            {
                "name": "HUAWEI Technologies Düsseldorf GmbH",
                "description": "Huawei is a leading global information and communications technology (ICT) solutions provider. In Europe, Huawei has currently over 13000 employees, some 2 400 of these work in highly skilled jobs, dedicated entirely to research, development and innovation, cooperating across the continent with more than 100 academic and research partners, investing over 75 Mio € p.a. in partnerships Huawei’s Research Centre in Munich, which belongs to the Huawei Technologies Düsseldorf GmbH (HWDU) legal entity, streamlines and manages Huawei’s Cloud, Computing and AI efforts at the European level. The Munich Research Centre (MRC), strong of its 500+ work force and focuses on research, development and standardisation in the areas of cloud management and high-performance computing, AI, audio and video technologies. All in all, the MRC has participated over the years in more than 35 EU framework programme funded projects as a beneficiary, spanning from FP7 to Horizon Europe.",
                "logo": "https://www.decice.eu/wp-content/uploads/2022/09/06-Huawei-Logo-200x126-1.png",
                "links": [
                    { "type": "home", "label": "Home", "url": "https://www.huawei.com/de/" },
                    { "type": "twitter", "label": "Twitter", "url": "https://twitter.com/Huawei_Germany" },
                    { "type": "facebook", "label": "Facebook", "url": "https://www.facebook.com/HuaweiGermany" },
                    { "type": "instagram", "label": "Instagram", "url": "https://www.instagram.com/huaweideutschland/" },
                    { "type": "linkedin", "label": "Linkedin", "url": "https://www.linkedin.com/company/huawei-germany" },
                    { "type": "youtube", "label": "Youtube", "url": "https://www.youtube.com/channel/UCFdUdFJchPtdxPlqy9hHmug" }
                ]
            },
            {
                "name": "SYNYO GmbH",
                "description": "SYNYO is a global-acting enterprise focusing on research, innovation and technology located in 3 offices in Vienna, Austria. SYNYO explores, develops and implements novel methods, approaches, technologies and solutions in various domains tackling societal, political, ecological and economical challenges. SYNYO analyses the impact of emerging technologies from different angles and from an interdisciplinary perspective. The team at SYNYO consists of high-skilled employees specialized in various scientific and technical fields like Social Sciences, Safety & Security, Energy & Sustainability, Urban Future, Smart Health, or Digital Systems, Smart Technologies. The team of SYNYO consists of 31 employees working on national and international projects.",
                "logo": "https://www.decice.eu/wp-content/uploads/2022/09/08-SYNYO-1-Logo-200x126-1.png",
                "links": [
                    { "type": "home", "label": "Home", "url": "https://www.synyo.com/" }
                ]
            },
            {
                "name": "Consorzio TOP-IX – Torino e Piemonte Exchange Point",
                "description": "TOP-IX (TOrino Piemonte Internet eXchange) is a non-profit consortium founded in 2002 with the aim of creating and managing an Internet Exchange (IX) for the exchange of Internet traffic in North-West Italy. Furthermore, TOP-IX promotes and supports, through the Development Program (DP), technological and business innovation projects based on the broadband Internet. The two actions act synergistically to promote the growth of the territory.",
                "logo": "https://www.decice.eu/wp-content/uploads/2022/09/10-top-ix-1-Logo-200x126-1.png",
                "links": [
                    { "type": "home", "label": "Home", "url": "https://www.top-ix.org/en/home-eng/" },
                    { "type": "twitter", "label": "Twitter", "url": "https://twitter.com/top_ix" },
                    { "type": "linkedin", "label": "Linkedin", "url": "https://www.linkedin.com/company/top-ix-consortium/" }
                ]
            },
            {
                "name": "Alma Mater Studiorum – Universita di Bologna",
                "description": "Almost 1000 years old, the University of Bologna (UNIBO) is known as the oldest University in the western world. Nowadays, UNIBO is one of the most important institutions of higher education across Europe and the second largest University in Italy with 11 Schools, 33 Departments and about 84.000 students; it is organized in a multi-campus structure with 5 operating sites (Bologna, Cesena, Forlì, Ravenna and Rimini), and, since 1998, also a permanent headquarters in Buenos Aires. With regard to its international reputation, UNIBO has been awarded the use of the logo “HR Excellence in Research” and is among the top 5 Italian universities in the main International rankings. The activity of the University of Bologna will be conducted within the Department of Electrical, Electronic and Information Engineering (DEI). DEI is one of the largest departments in UNIBOs with an excellent research profile, attracting more than 25% of UNIBOs overall EU funding. Within DEI, the research activity is carried out by the ECS Lab, covering areas related to compilers, programming models and architectures in the domain of both embedded and high-performance energy-efficient multi- and many-core systems on a chip and large-scale distributed system.",
                "logo": "https://www.decice.eu/wp-content/uploads/2022/09/11-unibo-Logo-200x126-1.png",
                "links": [
                    { "type": "home", "label": "Home", "url": "https://www.unibo.it/en" },
                    { "type": "twitter", "label": "Twitter", "url": "https://twitter.com/Unibo" },
                    { "type": "facebook", "label": "Facebook", "url": "https://www.facebook.com/unibo.it" },
                    { "type": "instagram", "label": "Instagram", "url": "https://www.instagram.com/unibo/" },
                    { "type": "linkedin", "label": "Linkedin", "url": "https://www.linkedin.com/school/unibo/" },
                    { "type": "youtube", "label": "Youtube", "url": "https://www.youtube.com/user/UniBologna" }
                ]
            },
            {
                "name": "Marmara University",
                "description": "Located in Istanbul, Marmara University is the largest university in Turkey with 16 faculties, 11 institutes, more than 80,000 students, and close to 3,500 academic personnel. VeNIT Research Lab is positioned at the Computer Engineering Department, Marmara University, conducts research in two main areas, (1) “V2X Communications/Networking/Internet of Things” and (2) “Artificial Intelligence/Machine Learning”, and is in strong collaboration with industry to propose innovative and promising solutions for real-world problems. In DECICE project, VeNIT Lab will contribute to Digital Twin, APIs, and communication approaches for the enhanced Edge-Cloud continuum. AI, ML, and image processing solutions will be developed and integrated with the platform that will be built in DECICE. We will lead a use case on Intelligent Intersection and VRU safety. In cooperation with the partners in DECICE, we will also evaluate and demonstrate project outputs with real field use cases for “Connected Autonomous Vehicle” and “Intelligent Intersection/VRU Safety” .",
                "logo": "https://www.decice.eu/wp-content/uploads/2022/09/09-Marmara-University-1-Logo-200x126-1.png",
                "links": [
                    { "type": "home", "label": "Home", "url": "http://www.marmara.edu.tr" },
                    { "type": "twitter", "label": "Twitter", "url": "https://twitter.com/marmara1883" },
                    { "type": "facebook", "label": "Facebook", "url": "https://www.facebook.com/marmara1883" },
                    { "type": "instagram", "label": "Instagram", "url": "https://www.instagram.com/marmara_univ/" },
                    { "type": "linkedin", "label": "Linkedin", "url": "https://www.linkedin.com/school/marmara1883" },
                    { "type": "youtube", "label": "Youtube", "url": "https://www.youtube.com/marmara1883" }
                ]
            },
            {
                "name": "BIGTRI Bilisim Anonim Sirketi",
                "description": "BigTRI is a spinoff company established by the researchers of VeNIT Lab, working on R&D projects with expertise on IoT, vehicular networks, computer vision and AI/ML. From research and prototyping to product development and branding, we build custom solutions for real world problems including but not limited to transportation systems, smart manufacturing, data infrastructures and retail. BigTRI creates a value chain between academy and industry through close collaboration. The company has services and innovative solutions for C-ITS applications and testing, network monitoring, AI/ML-based data infrastructures, edge&cloud computing, image processing, and smart manufacturing. In DECICE project, to which we will contribute with Artificial Intelligence, Digital Twin (DT) and Communication Optimization; DT and AI based resource management and scheduler will be developed, which allows to monitor the entire system in Edge and Cloud Computing architecture. We will also evaluate and demonstrate project outputs with real field use cases for “Connected Autonomous Vehicle” and “Smart Intersection/VRU Safety”.",
                "logo": "https://www.decice.eu/wp-content/uploads/2022/09/13-TRI-Logo-200x126-1.png",
                "links": [
                    { "type": "home", "label": "Home", "url": "https://www.bigtri.net/" },
                    { "type": "twitter", "label": "Twitter", "url": "https://twitter.com/bigtri_" },
                    { "type": "instagram", "label": "Instagram", "url": "https://www.instagram.com/bigtribilisim/" },
                    { "type": "linkedin", "label": "Linkedin", "url": "https://www.linkedin.com/company/bigtri" }
                ]
            },
            {
                "name": "The numerical Algorithms Group Limited",
                "description": "The Numerical Algorithms Group Limited (NAG) provides industry-leading numerical software and technical services to banking and finance, energy, engineering, and market research, as well as academic and government institutions. World-renowned for the NAG® Library – the most rigorous and robust collection of numerical algorithms available – NAG also offers Automatic Differentiation, Machine Learning, and Mathematical Optimization products, as well as world-class technical consultancy across HPC and Cloud HPC, code porting and optimisation, and other areas of numerical computing. Founded more than 50 years ago from a multi-university venture, NAG is headquartered in Oxford, UK with offices in the UK, US, EU, and Asia. For more information, visit nag.com/aboutus .",
                "logo": "https://www.decice.eu/wp-content/uploads/2025/10/NAG-Logo-blue-.png",
                "links": [
                    { "type": "home", "label": "Home", "url": "https://www.nag.com/" },
                    { "type": "twitter", "label": "Twitter", "url": "https://twitter.com/nagtalk" },
                    { "type": "facebook", "label": "Facebook", "url": "https://www.facebook.com/NAGTalk" },
                    { "type": "linkedin", "label": "Linkedin", "url": "https://www.linkedin.com/company/nag/" },
                    { "type": "github", "label": "Github", "url": "https://github.com/numericalalgorithmsgroup" },
                    { "type": "youtube", "label": "Youtube", "url": "https://www.youtube.com/user/NumericalAlgorithms" }
                ]
            }
        ]
    },
};

export const FALLBACK_NEWS = {
    source: "news",
    payload: {
        "fetched_at": "2025-11-25T14:57:24.799101",
        "items": [{
                "title": "DECICE Showcased at NexusForum2025 Summit in Brussels",
                "date": "November 17, 2025",
                "excerpt": null,
                "link": "https://www.decice.eu/project-news/decice-showcased-at-nexusforum2025-summit-in-brussels/",
                "content": "Brussels, 5–6 November 2025 – The DECICE consortium was delighted to participate in the NexusForum2025 Summit , a high-level gathering that brought together leading experts and initiatives working at the intersection of Artificial Intelligence, Cloud Computing, and Sustainability —three key pillars underpinning Europe’s Digital Sovereignty.\n\nDuring a dedicated session, the DECICE project coordinator presented the consortium’s journey and highlighted its major achievements. The presentation covered the project’s Key Exploitable Results (KERs) , the challenges addressed throughout the lifecycle, and the forward-looking roadmap designed to ensure continued innovation and impact beyond the project’s conclusion.\n\nThe Summit provided an excellent platform for knowledge exchange and collaboration , enabling DECICE to engage with other European research and innovation projects. Discussions focused on building synergies that strengthen Europe’s digital and technological resilience, while showcasing how DECICE’s outcomes contribute to advancing intelligent collaboration across the device–edge–cloud continuum.\n\nBy participating in NexusForum2025, DECICE reaffirmed its commitment to supporting Europe’s strategic ambitions in digital transformation and sustainability, while ensuring that its innovations remain accessible and impactful for diverse stakeholder communities.\n\nKey words: #DECICE #NexusForum2025 #AI #Cloud #Sustainability"
            },
            {
                "title": "Exploitation opportunities for TOP-IX within DECICE",
                "date": "November 7, 2025",
                "excerpt": null,
                "link": "https://www.decice.eu/project-news/exploitation-opportunities-for-top-ix-within-decice/",
                "content": "As we approach the conclusion of the DECICE project, TOP-IX is beginning to define the future exploitation of its outputs and key relevant results. This reflection is not only about consolidating the knowledge gained during the project, but also about situating DECICE within a broader roadmap where Internet Exchanges evolve into active players of Europe’s federated digital ecosystem.\n\nTraditionally, IXPs (Internet eXchange Points) have acted as neutral interconnection hubs, enabling networks to exchange traffic efficiently, with reduced latency and improved reliability. Yet today, new demands for distributed computing, data sovereignty and service orchestration are reshaping the digital infrastructure landscape.\n\nIn this context, TOP-IX envisions the evolution of the IXP into a Service Composition Point (SCP) — a neutral broker where services can be discovered, orchestrated and consumed across federated cloud and edge environments. DECICE contributes to this long-term vision by providing valuable building blocks: AI-driven orchestration mechanisms, validated use cases and insights into how workloads can be dynamically placed and adapted in distributed infrastructures.\n\nFederated services DECICE outcomes support our ambition to participate in a European Federation of Service Composition Points, complementing other initiatives such as DOME , Fluidos and Fulcrum . Together, they point towards a cohesive framework where marketplaces and orchestration converge to strengthen sovereignty and interoperability.\n\nMarketplace for members (Long-Term Vision) In the longer term, building on federated initiatives, TOP-IX aims to evolve its service offer into a marketplace of orchestrated resources. This could include access to edge computing, GPU-based inference, storage and AI-powered management — all accessible through our neutral interconnection hub. While still a roadmap item, this ambition illustrates how IXPs can progressively expand their role in the digital value chain.\n\nLiving testbed for startups Beyond validating technology, our infrastructure testbed represents a unique opportunity for startups and scaleups, who can experiment with advanced digital services in a neutral and production-like environment. This continues TOP-IX’s long-standing tradition of supporting entrepreneurship and innovation through its Development Program.\n\nInteroperability and compliance services As data spaces and federated infrastructures take shape in Europe, TOP-IX can use DECICE lessons (as well as inputs from other initiatives like Gaia-X and IDSA ) to provide interoperability services that meet the requirements of secure and sovereign data management and sharing.\n\nBusiness models and sustainability Beyond connectivity, IXPs like TOP-IX can explore future models such as subscription-based services, pay-per-use resource allocation, and transaction-fee schemes in federated marketplaces.\n\nDECICE has been a valuable step in our broader journey: it does not by itself redefine the Internet Exchange, but it strengthens our capacity to evolve into a neutral service broker and to actively contribute to Europe’s federated digital landscape.\n\nBy building on these synergies, TOP-IX can empower its community and play a strategic role in ensuring that Europe’s future cloud-to-edge ecosystem remains open, trustworthy and fair.\n\nAuthor(s): CHRISTIAN RACCA, TOrino Piemonte Internet eXchange\n\nKey words: #Federation #Orchestration #Interoperability #Marketplace #ServiceBroker"
            },
            {
                "title": "Connecting with Germany’s HPC Community – DECICE at NHR Conference 2025",
                "date": "November 4, 2025",
                "excerpt": null,
                "link": "https://www.decice.eu/project-news/connecting-with-germanys-hpc-community-decice-at-nhr-conference-2025/",
                "content": "The DECICE project is pleased to announce its participation in the NHR Conference 2025, which will take place on 22–25 September 2025 in Göttingen, Germany.\n\nOrganized by the Association for National High Performance Computing (NHR), this annual event brings together Germany’s national HPC centers and the wider scientific computing community to exchange experiences, share research updates, and strengthen collaboration in high-performance computing.\n\nThis year, the conference will focus on three key themes: AI in Social Sciences & Humanities, Life Science, and Data Management & Storage — covering topics from the methodological and interpretive impact of AI, to predictive and data-intensive life science research, and innovative approaches to efficient, scalable data handling in HPC environments.\n\nBy attending, DECICE aims to engage with HPC experts from across the national network, stay up to date on current developments in these research areas, and explore opportunities to further enhance its own work through the exchange of ideas, best practices, and future collaboration.\n\nFor more about the conference, visit: https://www.nhr-verein.de/conference\n\nAuthor(s): Mirac Aydin, Gesellschaft für Wissenschaftliche Datenverarbeitung MBH Göttingen\n\nKey words: #HPC #AIinResearch #LifeSciences #DataManagement #ScientificCollaboration"
            },
            {
                "title": "DECICE Enhances AI Scheduler and Digital Twin for Smarter, Greener Computing",
                "date": "November 4, 2025",
                "excerpt": null,
                "link": "https://www.decice.eu/project-news/decice-enhances-ai-scheduler-and-digital-twin-for-smarter-greener-computing/",
                "content": "The DECICE project has introduced important improvements to two of its key components — the AI Scheduler and the Digital Twin — further advancing intelligent, adaptive, and energy-efficient scheduling across the compute continuum.\n\nThe AI Scheduler now incorporates new predictive patterns for workload allocation. By analyzing historical trends alongside real-time system data, the scheduler can forecast resource demands more accurately, resulting in improved throughput, reduced latency, and a more balanced distribution of workloads.\n\nThe Digital Twin has also been upgraded with node-level power consumption metrics, enabling it to monitor energy usage for individual nodes. This enhancement supports energy-aware and carbon-aware scheduling by providing the AI Scheduler with precise data on power consumption. In addition, both the carbon intensity prediction model and the anomaly detection model have been tuned for higher accuracy and faster responsiveness, allowing for better prediction of environmental impact and earlier detection of irregular system behavior.\n\nWith access to more accurate and granular system insights, the AI Scheduler can now optimize workload placement not only for performance but also for energy efficiency and environmental impact. For example, it can prioritize running workloads on nodes with lower power usage or reduced carbon intensity, or proactively reroute jobs away from nodes showing early signs of anomalies.\n\nThese improvements strengthen DECICE’s abilities. By combining predictive intelligence with sustainability-focused decision-making, DECICE moves a step closer to achieving high-performance computing that is both powerful and environmentally responsible.\n\nAuthor(s): Felix Stein, University of Göttingen\n\nKey words: # AI Scheduler #Digital Twin #Energy Efficiency #Predictive Intelligence #Carbon-Aware Computing"
            },
            {
                "title": "Accelerating Cloud Robotics with Lightweight, Scalable DevOps",
                "date": "October 23, 2025",
                "excerpt": null,
                "link": "https://www.decice.eu/project-news/accelerating-cloud-robotics-with-lightweight-scalable-devops/",
                "content": "A lightweight and fully automated DevOps framework is now available to dramatically simplify the deployment of ROS2 applications on Kubernetes .\n\nThis solution tackles one of cloud robotics’ biggest pain points: the time and complexity required to provision, configure, and manage reproducible environments. Using Vagrant , Kubernetes , Docker/Helm , and a CI/CD pipeline , it takes users from zero to a fully operational ROS2 cluster with monitoring in just 13 minutes —more than 20× faster than manual methods.\n\nKey Highlights\n\n⚡ Rapid Deployment: Automated setup of Kubernetes clusters and ROS2 pods.\n\n📈 Scalability: Expands up to 326 pods in under 10 minutes, even on modest hardware.\n\n📊 Monitoring & Observability: Integrated Prometheus + Grafana dashboards for real-time insight.\n\n🛠️ Reproducibility: Vagrant-based VM provisioning eliminates the “works on my machine” problem.\n\n🔄 CI/CD Integration: GitHub Actions pipelines for seamless build, test, and deploy.\n\nThis framework offers a production-aligned, reproducible workflow that supports robotics developers, EU research projects, and industry partners working on edge-cloud systems, digital twins, and AI-driven robotics.\n\nAll source code, deployment scripts, and configuration files are open-source and available on GitHub: 🔗 github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment\n\nContributions are welcome.\n\nAuthor(s): Mohsen Seyedkazemi Ardebili, University of Bologna\n\nKey words: # ROS2 # Kubernetes # CI/CD pipeline # Prometheus # edge-cloud systems"
            },
            {
                "title": "DECICE Final Project Webinar",
                "date": "October 20, 2025",
                "excerpt": null,
                "link": "https://www.decice.eu/project-news/decice-final-webinar/",
                "content": "🗓️ Date: November 12, 2025\n\n⏱️ Time: 10:00 AM – 11:30 AM CET\n\n🌐 Location: Online (virtual event)\n\nThe final webinar of the DECICE project took place as a conclusive showcase of the outcomes of our EU-funded initiative focused on intelligent collaboration across the device-edge-cloud continuum. The session featured a strategic overview of the project’s innovations, a presentation of the developed solutions, and an in-depth exploration of three real-world use cases. Participants discovered how DECICE’s cognitive scheduling and orchestration technologies contributed to shaping the future of distributed computing. The webinar concluded with a live Q&A session, fostering dialogue and knowledge exchange among stakeholders."
            },
            {
                "title": "DECICE Framework Expands with Unified Workflow Support",
                "date": "October 17, 2025",
                "excerpt": null,
                "link": "https://www.decice.eu/project-news/decice-framework-expands-with-unified-workflow-support/",
                "content": "The DECICE framework has taken a significant step forward in workflow flexibility by introducing support for Snakemake and Argo Workflows in addition to native Kubernetes job definitions.\n\nPreviously, users could submit their computational jobs by providing a Kubernetes job definition YAML file along with any required input files. With our latest enhancement, users can now upload Snakemake files or Argo Workflow definitions, enabling seamless integration of workflows created in these popular workflow management systems.\n\nThis advancement brings workflow unification to DECICE. No matter which workflow format users choose, our internal parsers automatically convert the submitted files into the DECICE Workflow representation. This ensures that:\n\nSteps, dependencies, and execution order are preserved across formats\n\nWorkflows can be executed efficiently and consistently on a cluster\n\nUsers have more freedom to design and manage workflows in the tool of their choice without sacrificing compatibility\n\nBy supporting multiple workflow formats, DECICE enables researchers and engineers to run complex data processing pipelines and scientific workflows seamlessly across the entire compute continuum — from edge devices, through cloud platforms, and all the way to the largest high-performance computing (HPC) systems. This is achieved without the need for any manual file conversion or reconfiguration.\n\nWith this flexibility, users can create workflows in their preferred tools and deploy them anywhere within a federated, heterogeneous infrastructure. This capability not only saves valuable time but also fosters cross-platform interoperability, making it easier for research groups and organizations to collaborate and share workflows, regardless of how or where they were originally created.\n\nAuthor(s): Mirac Aydin, Gesellschaft für Wissenschaftliche Datenverarbeitung MBH Göttingen\n\nKey words: #DECICE #WorkflowIntegration #Snakemake #ArgoWorkflows #CrossPlatformInteroperability"
            },
            {
                "title": "DECICE AI Scheduler Innovation Selected for FTC 2025",
                "date": "October 9, 2025",
                "excerpt": null,
                "link": "https://www.decice.eu/project-news/decice-ai-scheduler-innovation-selected-for-ftc-2025/",
                "content": "We are pleased to announce that our paper, “Design and Implementation of Integrated AI Scheduler for Dynamic Cloud Workloads Allocation in Kubernetes Environments”, developed as part of the DECICE project, has been accepted for presentation at the Future Technologies Conference (FTC) 2025, taking place on 6–7 November 2025 in Munich, Germany.\n\nThe Future Technologies Conference is one of the world’s most anticipated interdisciplinary technology events, bringing together researchers, academics, industry leaders, and government representatives from over 50 countries. This global forum serves as a meeting point for exchanging ideas, presenting innovations, and shaping the technologies that will define our future.\n\nOur paper introduces an AI-driven approach to smarter and more efficient workload scheduling across the compute continuum — spanning devices, edge systems, cloud, and high-performance computing (HPC). This innovation aims to improve how computational tasks are distributed, enabling faster processing, higher efficiency, and more adaptive computing environments.\n\nFTC 2025 will provide an excellent opportunity to share this work with an international audience, gain valuable feedback from experts across multiple disciplines, and participate in discussions that will help shape the future of intelligent computing.\n\nWe look forward to contributing to this exciting event and showcasing how AI-powered scheduling can help build the backbone of tomorrow’s digital infrastructure.\n\nFor more information about FTC 2025, visit: https://saiconference.com/FTC\n\nAuthor(s): Felix Stein, Georg-August-Universität Göttingen Stiftung Öffentlichen Rechts\n\nKey words: #AIScheduler #CloudWorkloads #Kubernetes #FTC2025 #HPC"
            },
            {
                "title": "Distributed Application Setup for DECICE Tutorial at ISC",
                "date": "October 2, 2025",
                "excerpt": null,
                "link": "https://www.decice.eu/project-news/distributed-application-setup-for-decice-tutorial-at-isc/",
                "content": "DECICE focuses on complex applications that span the compute continuum, encompassing edge, cloud, and HPC resources. Using container technology to package application code along with its dependencies into portable units simplifies the deployment of applications in a heterogeneous computing continuum. At ISC 2025, a tutorial organized by DECICE focused on containerizing and orchestrating distributed applications across the compute continuum. In this blog, we share how we set up an edge infrastructure, integrated it with the cloud for orchestration, and enabled participants to deploy distributed applications.\n\nDuring the hands-on session, participants deployed a speech-to-text application composed of machine learning–based transcription and inference services. The application captured speech, transcribed it to text, used an LLM to perform inference on the text, and displayed the result. Transcription was executed at the edge, while inference was offloaded to the cloud. Although both tasks could run at the edge, the larger models required for accurate inference exceeded the capacity of the edge nodes. Alternatively, streaming raw audio to the cloud was possible, but it was bandwidth-intensive. To address this, we used an efficient approach in which transcription was performed at the edge, the resulting text was sent to the cloud via lightweight protocols such as MQTT, and inference was performed in the cloud. In addition to familiarizing participants with basic containerization and orchestration, the chosen application also exposed them to ML deployments and techniques for accessing hardware devices such as microphones from within containers.\n\nFor running speech transcription at the edge, we chose a Raspberry Pi 5 device due to its portability and low cost, while providing sufficient compute power to run lightweight containers. We attached a microphone and a USB display to the Raspberry Pi for recording speech and displaying the output, respectively. The USB display was flashed with a custom firmware that enables it to accept serial commands. The cloud component was powered by a Kubernetes instance in Huawei’s HAICGU cluster. The Raspberry Pi edge nodes were integrated with this Kubernetes setup using KubeEdge, a framework for extending Kubernetes orchestration capability to remote edge nodes. We used the pi-gen tool to create an image for the Raspberry Pi. We forked the tool’s repository, added the necessary scripts to download, install, and configure KubeEdge, and then prepared the boot image for the Raspberry Pi. Upon booting the Raspberry Pi with this image, it automatically runs KubeEdge and registers itself as a node in the HAICGU Kubernetes cluster. This setup enabled the participants to interact with the Kubernetes at the cloud and deploy containers across the cloud and the edge nodes. The cloud login node had Podman to provide the participants with the ability to build images and push them to a private container registry deployed by the tutorial team.\n\nThe participants needed access to the Kubernetes API in the cloud for submitting the workloads and deploying the application in the continuum. For security reasons, the Kubernetes API server was not exposed to the internet, and the participants had to ssh into the HAICGU cluster login node to access the API server. The challenge in this approach is with configuring the ssh clients of each participant to access the cluster. To simplify the process, the tutorial team deployed a browser based terminal solution using wetty. A landing page was deployed at HLRS, which gave participants access to a browser–based terminal session on an HLRS VM. This terminal session was preconfigured with SSH client settings, enabling participants to easily connect to the HAICGU cluster login node.\n\nTo transcribe speech at the edge, participants deployed a container with whisper.cpp library and sound libraries on a Raspberry Pi with an attached microphone. Whisper.cpp was chosen for its lightweight, efficient implementation of the Whisper model, enabling offline transcription on resource-constrained edge devices. For inference, we used Ollama, an open-source tool for running large language models (LLMs). We went with Ollama because of its ease of deployment compared to other inference tools such as vLLM. A container running the Ollama server was deployed on the cloud to receive the text generated at the edge and return the inference results. To display the inference output at the edge, a separate container was deployed on the edge device, receiving results from the cloud and sending serial commands to the USB display. The different application components coordinated with each other by subscribing and publishing messages to a containerized MQTT broker in the cloud. We provided participants with Dockerfiles to build the container images on the cloud infrastructure and push them to a dedicated tutorial registry. Participants were also given manifests to deploy these components on the appropriate nodes using Kubernetes. Refer to this readme and the contents here for more information.\n\nThis multi-component, containerized application is a simple representation of the use cases addressed by the DECICE project. The scheduler and the framework developed within the DECICE project will enhance such deployments by optimizing the component placement across the compute continuum by taking into account the various factors like latency, compute power, and power consumption. This setup not only demonstrated the technical feasibility of distributed deployment across the compute continuum using containers but also highlighted the practical considerations that DECICE aims to address.\n\nAuthor(s): Aadesh Baskar, University of Stuttgart\n\nKey words: #Compute Continuum #Containerization #Telecommunication & Orchestration #Speech-to-Text Application #Scalability & Optimization"
            }
        ]
    },
};