import Link from "next/link";
import {
  ArrowRight,
  ArrowUpRight,
  ChartNoAxesCombined,
  FileSpreadsheet,
  LockKeyhole,
  Repeat2,
  Sparkles,
  Wallet,
} from "lucide-react";

export default function Home() {
  return (
    <div className="landing">
      <header className="landing-nav">
        <Link className="brand" href="/">
          <span className="brand-mark">
            <Wallet size={20} />
          </span>
          <span>
            where<span className="brand-light">money</span>
          </span>
        </Link>
        <div>
          <Link href="/login">Log in</Link>
          <Link className="button button-primary" href="/signup">
            Get started <ArrowRight size={16} />
          </Link>
        </div>
      </header>
      <main className="landing-main">
        <div className="landing-copy">
          <span className="hero-pill">
            <Sparkles size={14} /> Your money story, made simple
          </span>
          <h1>
            Know where your money <em>really</em> goes.
          </h1>
          <p>
            Turn bank CSV statements into a clear, calm picture of your
            spending. No bank connection. No judgment. Just useful answers.
          </p>
          <div className="hero-actions">
            <Link className="button button-primary button-lg" href="/signup">
              Explore your spending <ArrowRight size={18} />
            </Link>
            <Link className="text-link" href="/login">
              Already have an account? <ArrowUpRight size={16} />
            </Link>
          </div>
          <div className="trust-line">
            <LockKeyhole size={16} /> Your data belongs to you. Export or delete
            it anytime.
          </div>
        </div>
        <div className="hero-preview">
          <div className="preview-head">
            <span className="preview-dot" /> Your spending snapshot{" "}
            <span>September 2026</span>
          </div>
          <div className="preview-total">
            <small>Total spending</small>
            <strong>$1,837.42</strong>
            <span>↓ A clearer picture starts here</span>
          </div>
          <div className="preview-bars">
            <div>
              <span>Housing</span>
              <i style={{ width: "82%" }} />
              <b>$600</b>
            </div>
            <div>
              <span>Food & dining</span>
              <i style={{ width: "61%" }} />
              <b>$438</b>
            </div>
            <div>
              <span>Shopping</span>
              <i style={{ width: "42%" }} />
              <b>$302</b>
            </div>
            <div>
              <span>Transportation</span>
              <i style={{ width: "22%" }} />
              <b>$144</b>
            </div>
          </div>
          <div className="preview-footer">
            Illustrative example · Your dashboard uses only your uploads
          </div>
        </div>
      </main>
      <section className="landing-features">
        <div>
          <FileSpreadsheet size={23} />
          <h3>Upload a CSV</h3>
          <p>
            Bring statements from your bank. Preview every import before it
            becomes part of your dashboard.
          </p>
        </div>
        <div>
          <ChartNoAxesCombined size={23} />
          <h3>See the whole picture</h3>
          <p>
            Understand categories, merchants, trends and what changed month to
            month.
          </p>
        </div>
        <div>
          <Repeat2 size={23} />
          <h3>Spot the regulars</h3>
          <p>
            Find recurring charges and upcoming expenses, clearly labeled as
            estimates.
          </p>
        </div>
      </section>
      <footer className="landing-bottom">
        Where Did My Money Go? · Personal spending intelligence, without the
        noise.
      </footer>
    </div>
  );
}
