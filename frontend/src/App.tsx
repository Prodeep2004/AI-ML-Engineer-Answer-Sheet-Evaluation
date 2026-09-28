import { useEffect, useState } from 'react'
import Home from './pages/Home'
import EvaluationView from './pages/EvaluationView'
import Rubrics from './pages/Rubrics'
import RubricEditor from './pages/RubricEditor'

function useRoute() {
  const read = () => location.hash.replace(/^#/, '') || '/'
  const [route, setRoute] = useState(read)
  useEffect(() => {
    const on = () => { setRoute(read()); window.scrollTo(0, 0) }
    addEventListener('hashchange', on)
    return () => removeEventListener('hashchange', on)
  }, [])
  return route
}

export default function App() {
  const route = useRoute()
  const parts = route.split('/').filter(Boolean)

  let page
  if (parts[0] === 'e' && parts[1]) page = <EvaluationView id={parts[1]} key={parts[1]} />
  else if (parts[0] === 'rubrics' && parts[1]) page = <RubricEditor id={decodeURIComponent(parts[1])} key={parts[1]} />
  else if (parts[0] === 'rubrics') page = <Rubrics />
  else page = <Home />

  const section = parts[0] === 'rubrics' ? 'rubrics' : 'evaluate'
  return (
    <>
      <header className="topbar">
        <a href="#/" className="wordmark">Marksheet<span className="tick">✓</span></a>
        <nav>
          <a href="#/" className={section === 'evaluate' ? 'on' : ''}>Evaluate</a>
          <a href="#/rubrics" className={section === 'rubrics' ? 'on' : ''}>Rubrics</a>
        </nav>
      </header>
      <main>{page}</main>
      <footer className="foot">Handwriting read, scored against your rubric, and flagged when unsure.</footer>
    </>
  )
}
