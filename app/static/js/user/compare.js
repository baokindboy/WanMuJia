var Compare=React.createClass({displayName:"Compare",getInitialState:function(){return{firstData:null,secondData:null,firstID:null,secondID:null}},getData:function(e,t){$.ajax({url:e,dataType:"json",success:function(e){"firstData"==t?this.setState({firstData:e}):"secondData"==t&&this.setState({secondData:e})}.bind(this),error:function(t,a,s){console.error(e,a,s.toString())}.bind(this)})},componentDidMount:function(){var e=this.props.setCompareItem.getItem();if(e[0]){this.setState({firstID:e[0]});var t="/item/"+e[0]+"?format=json";this.getData(t,"firstData")}if(e[1]){this.setState({secondID:e[1]});var a="/item/"+e[1]+"?format=json";this.getData(a,"secondData")}},deleteItem:function(e){"first"==e?(this.props.setCompareItem.deleteItem(this.state.firstID),this.props.CompareBarDel(this.state.firstID),this.setState({firstData:null}),this.setState({firstID:null})):"second"==e&&(this.props.setCompareItem.deleteItem(this.state.secondID),this.props.CompareBarDel(this.state.secondID),this.setState({secondData:null}),this.setState({secondID:null}))},render:function(){return React.createElement("div",{className:"compare"},React.createElement("div",{className:"wrapper-cmp"},React.createElement("h3",null,"产品对比"),React.createElement(CompareItembox,{deleteItem:this.deleteItem,firstImgSrc:this.state.firstData?this.state.firstData.image_url:null,secondImgSrc:this.state.secondData?this.state.secondData.image_url:null,firstID:this.state.firstID,secondID:this.state.secondID}),this.state.firstData&&this.state.secondData?React.createElement(CompareTable,{firstData:this.state.firstData,secondData:this.state.secondData}):null))}}),CompareItembox=React.createClass({displayName:"CompareItembox",render:function(){return React.createElement("div",{className:"compare-img clearfix"},React.createElement(CompareItem,{deleteItem:this.props.deleteItem,pos:"first",imgSrc:this.props.firstImgSrc,aHref:this.props.firstID}),React.createElement(CompareItem,{deleteItem:this.props.deleteItem,pos:"second",imgSrc:this.props.secondImgSrc,aHref:this.props.secondID}))}}),CompareItem=React.createClass({displayName:"CompareItem",handleDeleteClick:function(){this.props.deleteItem(this.props.pos)},render:function(){return React.createElement("div",{className:this.props.pos},this.props.aHref?React.createElement("a",{href:"/item?id="+this.props.aHref},React.createElement("img",{src:this.props.imgSrc,alt:""})):React.createElement("span",{className:"add-compare"},React.createElement("a",{href:"#ad",className:"add-compare-btn"},"+")),this.props.aHref?React.createElement("span",{className:"delete-compare-btn",onClick:this.handleDeleteClick},"删除"):null)}}),CompareTable=React.createClass({displayName:"CompareTable",render:function(){return React.createElement("table",{className:"compare-params"},React.createElement("tbody",null,React.createElement(CompareTableItem,{first:this.props.firstData.item,second:this.props.secondData.item},"商品名称"),React.createElement(CompareTableItem,{first:this.props.firstData.size,second:this.props.secondData.size},"商品尺寸"),React.createElement(CompareTableItem,{first:this.props.firstData.area,second:this.props.secondData.area},"适用面积"),React.createElement(CompareTableItem,{first:this.props.firstData.price,second:this.props.secondData.price},"指导价格"),React.createElement(CompareTableItem,{first:this.props.firstData.second_scene,second:this.props.secondData.second_scene},"场景分类"),React.createElement(CompareTableItem,{first:this.props.firstData.category,second:this.props.secondData.category},"商品种类"),React.createElement(CompareTableItem,{first:this.props.firstData.second_material,second:this.props.secondData.second_material},"商品材料"),React.createElement(CompareTableItem,{first:this.props.firstData.stove,second:this.props.secondData.stove},"烘干工艺"),React.createElement(CompareTableItem,{first:this.props.firstData.outside_sand,second:this.props.secondData.outside_sand},"外表面打磨砂纸"),React.createElement(CompareTableItem,{first:this.props.firstData.inside_sand,second:this.props.secondData.inside_sand},"内表面打磨砂纸"),React.createElement(CompareTableItem,{first:this.props.firstData.carve,second:this.props.secondData.carve},"雕刻工艺"),React.createElement(CompareTableItem,{first:this.props.firstData.paint,second:this.props.secondData.paint},"涂饰工艺"),React.createElement(CompareTableItem,{first:this.props.firstData.decoration,second:this.props.secondData.decoration},"装饰工艺"),React.createElement(CompareTableItem,{first:this.props.firstData.tenon,second:this.props.secondData.tenon},"榫卯结构")))}}),CompareTableItem=React.createClass({displayName:"CompareTableItem",optionArrayItemDetail:function(e){if("[object Array]"===Object.prototype.toString.call(e)&&e.length>1)for(var t=0;t<e.length-1;t++)e[t]+="、";return e},render:function(){var e=this.optionArrayItemDetail(this.props.first),t=this.optionArrayItemDetail(this.props.second);return React.createElement("tr",{className:"param"},React.createElement("td",{className:"first"},e),React.createElement("td",{className:"param-name"},this.props.children),React.createElement("td",{className:"second"},t))}}),Compare=React.render(React.createElement(Compare,{CompareBarDel:CompareBarCom.deleteItem,setCompareItem:setCompareItem}),document.getElementById("compare"));