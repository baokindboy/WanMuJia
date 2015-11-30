'use strict';

//  ==================================================
//  Component: Header
//
//  Props: mainNav => object 主导航数据
//         shrink => boolean 主导航是否折叠
//
//  State: userInfo => object|null 登录状态
//         itemGroupData => object 商品组数据
//
//  Dependence: ItemGroup Header Slider Footer
//
//  TODO:
//  ==================================================

require('../../assets/pages/index.html');
require('./Home.scss');

let utils = require('../../lib/utils/utils');
let Ajax = require('reqwest');

let React = require('react');
let ReactDOM = require('react-dom');

let ItemGroup = require('./views/ItemGroup/ItemGroup.jsx');
let Elevator = require('./views/Elevator/Elevator.jsx');
let Header = require('../../lib/components/Header/Header.jsx');
let Slider = require('../../lib/components/Slider/Slider.jsx');
let Footer = require('../../lib/components/Footer/Footer.jsx');

const SLIDER_IMG = [
  {
    title: '劲飞红木',
    img: require('../../assets/images/slider_01_brand_jf.png'),
    url: '/12806'
  }, {
    title: '东城红木',
    img: require('../../assets/images/slider_02_brand_dc.png'),
    url: '/12836'
  }, {
    title: '君得益红木',
    img: require('../../assets/images/slider_03_brand_jdy.png'),
    url: '/12803'
  }, {
    title: '九龙堂红木',
    img: require('../../assets/images/slider_04_brand_jlt.png'),
    url: '/brand/12801'
  }
];

const ELEVATOR_ITEMS = [
  {
    id: 3,
    title: '客厅',
    offset: ''
  }, {
    id: 4,
    title: '卧室',
    offset: ''
  }, {
    id: 5,
    title: '厨卫',
    offset: ''
  }
];

let Home = React.createClass({
  getInitialState: function() {
    return {
      userInfo: null,  // 登录状态
      itemGroupData: {}  // 商品组数据
    };
  },
  componentDidMount: function() {
    let _this = this;
    Ajax({  // 获取个人信息
      url: '/logined',
      method: 'get',
      success: function (res) {
        if(res.logined) {
          _this.setState({
            userInfo: res
          });
        }
      }
    })
    Ajax({  // 获取商品组信息
      url: '/navbar',
      method: 'get',
      success: function (res) {
        _this.setState({
          itemGroupData: res
        });
      }
    })
  },
  render: function() {
    let colors = [
      '#6e3800',
      '#5f0077',
      '#3abfb4'
    ];
    return (
      <div>
        <Header
          userInfo={this.state.userInfo}
          shrink={false}
        >
          <Slider slides={SLIDER_IMG} />
        </Header>
        {Object.keys(this.state.itemGroupData).map((item, i) => {
          let guide = {
            title: this.state.itemGroupData[item].scene,
            img: '',
            url: '/item/?scene=' + item,
            color: colors[i]
          };
          return (
            <ItemGroup
              key={i}
              guide={guide}
              items={this.state.itemGroupData[item].items}
              color={colors[i]}
            />
          );
        })}
        <Elevator items={ELEVATOR_ITEMS} />
        <Footer />
      </div>
    );
  }
});

ReactDOM.render(
  <Home />,
  document.getElementById('content')
);
