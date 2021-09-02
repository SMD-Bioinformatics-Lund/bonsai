import { BrowserRouter as Router, Switch, Route } from 'react-router-dom'

import Species from './SpeciesSelection';
import Samples from './SamplesPage';

function App() {
  return (
    <Router>
      <Switch>
        <Route path='/' exact component={Species}/>
        <Route path='/:specie' component={Samples}/>
      </Switch>
    </Router>
  );
}

export default App;
