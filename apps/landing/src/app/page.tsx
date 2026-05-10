import LandingNavbar from './_components/navbar';
import Hero from './_components/hero';
import TrustBar from './_components/trust-bar';
import ServicesGrid from './_components/services-grid';
import Capabilities from './_components/capabilities';
import HowItWorks from './_components/how-it-works';
import StatsSection from './_components/stats-section';
import Testimonials from './_components/testimonials';
import CtaSection from './_components/cta-section';
import LandingFooter from './_components/footer';

export default function HomePage() {
  return (
    <>
      <LandingNavbar />
      <main>
        <Hero />
        <TrustBar />
        <ServicesGrid />
        <Capabilities />
        <HowItWorks />
        <StatsSection />
        <Testimonials />
        <CtaSection />
      </main>
      <LandingFooter />
    </>
  );
}
