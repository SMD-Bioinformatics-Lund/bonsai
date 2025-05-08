console.log("Hello");

const sampleEntry = (info) => {
    return String.raw`
    <div>${info}</div>
    `
}

const template = document.createElement("template");
template.innerHTML = String.raw`
    <style>
        #mytext {
            color: blue;
        }
    </style>
    <div id="mytext">Hello world from web component</div>
`;


class HelloWorld extends HTMLElement {

    root;
    myTextElem;

    constructor() {
        super();
        this.root = this.attachShadow({ mode: "open" });
        this.root.appendChild(template.content.cloneNode(true));
    }

    connectedCallback() {
        this.myTextElem = this.root.querySelector("#mytext");
    }
    
    initialize(samples) {
        for (const sample of samples) {

            // const sampleWc = new SampleWebComponent();
            // samplewC.initialize(sample);
            // this.myTextElem.appendChild()

            const sampleDiv = sampleEntry(sample);
            this.myTextElem.appendChild(sampleDiv);
        }
    }
}

customElements.define("hello-world", HelloWorld);
