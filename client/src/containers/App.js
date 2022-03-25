import { BrowserRouter as Router, Switch, Route } from 'react-router-dom'

import Groups from './GroupSelection';
import Samples from './SamplesPage';

function App() {
  return (
    <Router>
      <Switch>
        <Route path='/' exact component={Groups}/>
        <Route path='/:group' component={Samples}/>
      </Switch>
    </Router>
  );
}

export default App;
